import os
import re
import logging
from natsort import natsorted
from cached_property import cached_property
from . import utils
from .cycle import Cycle

logger = logging.getLogger(__name__)


def determine_plate_dimensions(n_wells):
    '''
    Determine the dimensions of a well plate.

    Parameters
    ----------
    n_wells: int
        number of wells in the plate

    Returns
    -------
    Tuple[int]
        number of rows and column in the well plate
    '''
    if n_wells == 96:
        return (8, 12)
    elif n_wells == 384:
        return (16, 24)
    elif n_wells == 1:
        return (1, 1)


class Plate(object):

    '''
    A well plate represents a container with multiple reservoirs for different
    samples (wells) that might be stained independently, but imaged under the
    same conditions.

    There are different well plate *formats*, which encode the number of wells
    in the well, e.g. "384".

    Note
    ----
    For consistency, a *slide* also represents a plate, which has only a single
    well with one sample that is stained and imaged under the same conditions.
    '''

    SUPPORTED_PLATE_FORMATS = {1, 96, 384}

    def __init__(self, plate_dir, cfg, user_cfg, library):
        '''
        Initialize an instance of class WellPlate.

        Parameters
        ----------
        plate_dir: str
            absolute path to plate folder
        cfg: TmlibConfigurations
            configuration settings for names of directories and files on disk
        library: str
            image library that should be used
            (options: ``"vips"`` or ``"numpy"``)

        See also
        --------
        `tmlib.cfg_setters.TmlibConfiguration`_
        `tmlib.cfg`_
        '''
        self.plate_dir = plate_dir
        self.cfg = cfg
        self.user_cfg = user_cfg
        self.library = library

    @property
    def name(self):
        '''
        Returns
        -------
        str
            name of the experiment
        '''
        self._name = os.path.basename(self.plate_dir)
        return self._name

    @property
    def dir(self):
        '''
        Returns
        -------
        str
            absolute path to the experiment directory
        '''
        return self.plate_dir

    def _is_cycle_dir(self, folder):
        format_string = self.cfg.CYCLE_DIR
        regexp = utils.regex_from_format_string(format_string)
        return True if re.match(regexp, folder) else False

    @property
    def cycles(self):
        '''
        Returns
        -------
        List[Cycle]
            configured cycle objects

        See also
        --------
        `tmlib.cycle.Cycle`_
        '''
        cycle_dirs = [
            os.path.join(self.dir, d)
            for d in os.listdir(self.dir)
            if os.path.isdir(os.path.join(self.dir, d))
            and self._is_cycle_dir(d)
            and not d.startswith('.')
        ]
        cycle_dirs = natsorted(cycle_dirs)
        self._cycles = [
                Cycle(d, self.cfg, self.user_cfg, self.library)
                for d in cycle_dirs
            ]
        return self._cycles

    @property
    def reference_cycle(self):
        '''
        Returns
        -------
        str
            name of the reference cycle

        Note
        ----
        If the attribute is not set, an attempt will be made to retrieve the
        information from the user configuration file. If the information is
        not available via the file, the last cycle is by default assigned as
        reference.
        '''
        if 'REFERENCE_CYCLE' in self.user_cfg.keys():
            self._reference_cycle = self.user_cfg.REFERENCE_CYCLE
            logger.debug('set reference cycle according to user configuration')
        else:
            cycle_names = natsorted([cycle.name for cycle in self.cycles])
            self._reference_cycle = cycle_names[-1]
            logger.debug('take last cycle as reference cycle')
        return self._reference_cycle

    def append_cycle(self):
        '''
        Create a new cycle object and add it to the end of the list of
        existing cycles.

        Returns
        -------
        WellPlate or Slide
            configured cycle object
        '''
        new_cycle_name = self.cfg.CYCLE_DIR.format(
                                    plate_dir=self.dir,
                                    sep=os.path.sep,
                                    cycle_id=len(self.cycles))
        new_cycle_dir = os.path.join(self.dir, new_cycle_name)
        logger.debug('add cycle: %s', os.path.basename(new_cycle_dir))
        logger.debug('create directory for new cycle: %s', new_cycle_dir)
        os.mkdir(new_cycle_dir)
        new_cycle = Cycle(new_cycle_dir, self.cfg, self.user_cfg, self.library)
        self.cycles.append(new_cycle)
        return new_cycle

    @property
    def n_wells(self):
        '''
        Returns
        -------
        plate_format: int
            number of wells in the plate

        Note
        ----
        Information is obtained from user configurations.

        Raises
        ------
        ValueError
            when provided plate format is not supported
        '''
        self._n_wells = self.user_cfg.NUMBER_OF_WELLS
        if self._plate_format not in self.SUPPORTED_PLATE_FORMATS:
            raise ValueError(
                    'Well plate format must be either "%s"' % '" or "'.join(
                            [str(e) for e in self.SUPPORTED_PLATE_FORMATS]))
        return self._n_wells

    @property
    def dimensions(self):
        '''
        Returns
        -------
        Tuple[int]
            number of wells in the plate on the vertical and horizontal axis,
            i.e. number of rows and columns
        '''
        return determine_plate_dimensions(self.n_wells)

    @property
    def well_coordinates(self):
        '''
        Returns
        -------
        List[Tuple[int]]
            zero-based row, column position of each well in the plate
        '''
        self._well_coordinates = [
            (self.map_well_id_to_coordinate(w)[0]-1,
             self.map_well_id_to_coordinate(w)[1]-1)
            for w in self.wells
        ]
        return self._well_coordinates

    @cached_property
    def wells(self):
        '''
        Returns
        -------
        Set[str]
            identifier string (capital letter for row position and
            one-based index number for column position) for each imaged
            well of the plate
        '''
        # TODO
        self._wells = set([md.well_id for md in self.image_metadata])
        return self._wells

    @property
    def n_acquired_wells(self):
        '''
        Returns
        -------
        int
            number of imaged wells in plate
        '''
        return len(set(self.well_coordinates))

    @staticmethod
    def map_well_id_to_coordinate(well_id):
        '''
        Mapping of the identifier string representation to the
        one-based index position, e.g. "A02" -> (1, 2)

        Parameters
        ----------
        well_id: str
            identifier string representation of a well

        Returns
        -------
        Tuple[int]
            one-based row, column position of a given well within the plate

        Examples
        --------
        >>>WellPlate.map_well_id_to_coordinate("A02")
        (1, 2)
        '''
        row_name, col_name = re.match(r'([A-Z])(\d{2})', well_id).group(1, 2)
        row_index = utils.map_letter_to_number(row_name)
        col_index = int(col_name)
        return (row_index, col_index)

    @staticmethod
    def map_well_coordinate_to_id(well_position):
        '''
        Mapping of the one-based index position to the identifier string
        representation.

        Parameters
        ----------
        well_position: Tuple[int]
            one-based row, column position of a given well within the plate

        Returns
        -------
        str
            identifier string representation of a well

        Examples
        --------
        >>>WellPlate.map_well_coordinate_to_id((1, 2))
        "A02"
        '''
        row_index, col_index = well_position[0], well_position[1]
        row_name = utils.map_number_to_letter(row_index)
        return '%s%.2d' % (row_name, col_index)
