import os
import re
import logging
import numpy as np
from natsort import natsorted
from cached_property import cached_property
from . import utils
from .cycle import Cycle
from .errors import RegexError

logger = logging.getLogger(__name__)


def determine_plate_dimensions(n_wells):
    '''
    Determine the dimensions of a well plate given the number of wells in the
    plate.

    Parameters
    ----------
    n_wells: int
        number of wells in the plate

    Returns
    -------
    Tuple[int]
        number of rows and column in the well plate
    '''
    plate_dimensions = {
        1: (1, 1),
        96: (8, 12),
        384: (16, 24)
    }
    return plate_dimensions[n_wells]


class Plate(object):

    '''
    A well plate represents a container with multiple reservoirs for different
    samples (wells) that might be stained independently, but imaged under the
    same conditions.

    There are different plate *formats*, which encode the number of wells
    in the plate, e.g. "384".

    Note
    ----
    For consistency, a *slide* is also represented as a plate, which has only
    a single well with one sample that is stained and imaged under the same
    conditions.
    '''

    SUPPORTED_PLATE_FORMATS = {1, 96, 384}

    PLATE_DIR_FORMAT = 'plate_{name}'

    def __init__(self, plate_dir, user_cfg, library):
        '''
        Initialize an instance of class WellPlate.

        Parameters
        ----------
        plate_dir: str
            absolute path to plate folder
        user_cfg: tmlib.cfg.UserConfigurations
            user configuration settings
        library: str
            image library that should be used
            (options: ``"vips"`` or ``"numpy"``)

        Returns
        -------
        tmlib.plate.Plate

        See also
        --------
        :mod:`tmlib.cfg.UserConfiguration`
        '''
        self.plate_dir = plate_dir
        self.user_cfg = user_cfg
        self.library = library

    @property
    def dir(self):
        '''
        Returns
        -------
        str
            absolute path to the plate directory
        '''
        return self.plate_dir

    @property
    def name(self):
        '''
        Returns
        -------
        str
            name of the plate
        '''
        regex = utils.regex_from_format_string(self.PLATE_DIR_FORMAT)
        match = re.search(regex, self.dir)
        if not match:
            raise RegexError(
                    'Plate name could not be determined from folder name')
        return match.group('name')

    def _is_cycle_dir(self, folder):
        format_string = Cycle.CYCLE_DIR_FORMAT
        regexp = utils.regex_from_format_string(format_string)
        return True if re.match(regexp, folder) else False

    @property
    def cycles(self):
        '''
        Returns
        -------
        List[tmlib.cycle.Cycle]
            configured cycle objects
        '''
        cycle_dirs = [
            os.path.join(self.dir, d)
            for d in os.listdir(self.dir)
            if os.path.isdir(os.path.join(self.dir, d))
            and self._is_cycle_dir(d)
            and not d.startswith('.')
        ]
        cycle_dirs = natsorted(cycle_dirs)
        return [Cycle(d, self.user_cfg, self.library) for d in cycle_dirs]

    def add_cycle(self):
        '''
        Add a cycle to the plate, i.e. create a folder on disk and append the
        list of existing cycle objects.

        Returns
        -------
        tmlib.cycle.Cycle
            configured cycle object
        '''
        cycle_index = len(self.cycles)
        new_cycle_name = Cycle.CYCLE_DIR_FORMAT.format(cycle_ix=cycle_index)
        new_cycle_dir = os.path.join(self.dir, new_cycle_name)
        if os.path.exists(new_cycle_dir):
            raise OSError('Cycle "%s" already exists.')
        logger.debug('add cycle: %s', cycle_index)
        logger.debug('create directory for new cycle: %s', new_cycle_dir)
        os.mkdir(new_cycle_dir)
        new_cycle = Cycle(new_cycle_dir, self.user_cfg, self.library)
        self.cycles.append(new_cycle)
        return new_cycle

    @property
    def n_wells(self):
        '''
        Returns
        -------
        int
            number of wells in the plate

        Note
        ----
        Information is obtained from user configurations.

        Raises
        ------
        ValueError
            when provided plate format is not supported
        '''
        self._n_wells = self.user_cfg.number_of_wells
        if self._n_wells not in self.SUPPORTED_PLATE_FORMATS:
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
        List[str]
            identifier string (capital letter for row position and
            one-based index number for column position) for each imaged
            well of the plate
        '''
        # TODO
        md = self.cycles[0].image_metadata_table
        self._wells = np.unique(md['well_name']).tolist()
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
