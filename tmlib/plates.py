import os
import re
from .cycle import Cycle


class WellPlate(Cycle):

    def __init__(self, cycle_dir, cfg, user_cfg, plate_format):
        '''
        Initialize an instance of class WellPlate.

        Parameters
        ----------
        cycle_dir: str
            absolute path to the cycle directory
        cfg: Dict[str, str]
            configuration settings
        user_cfg: Dict[str, str]
            additional user configuration settings
        plate_format: int
            number of wells in the plate (supported: 96 or 384)
        '''
        super(WellPlate, self).__init__(cycle_dir, cfg, user_cfg)
        self.cycle_dir = os.path.abspath(cycle_dir)
        self.cfg = cfg
        self.user_cfg = user_cfg
        self.plate_format = plate_format

    @property
    def dimensions(self):
        '''
        Returns
        -------
        Tuple[int]
            total number of rows and columns in the plate
        '''
        if self.plate_format == 96:
            self._dimensions = (8, 12)
        elif self.plate_format == 384:
            self._dimensions = (16, 24)
        return self._dimensions

    @property
    def plate_coordinates(self):
        '''
        Returns
        -------
        List[Tuple[int]]
            one-based row, column position of each well in the plate
        '''
        self._plate_coordinates = [self.id_to_position(w) for w in self.wells]
        return self._plate_coordinates

    @property
    def wells(self):
        '''
        Returns
        -------
        List[str]
            well identifier string: capital letter for row position and
            number for column position
        '''
        self._wells = [md.well for md in self.image_metadata]
        return self._wells

    @property
    def n_wells(self):
        '''
        Returns
        -------
        int
            number of used wells in plate
        '''
        self._n_wells = len(set(self.well_positions))
        return self._n_wells

    @staticmethod
    def name_to_index(name):
        '''
        Translate row name to index.

        Parameters
        ----------
        name: str
            capital letter

        Returns
        -------
        int
            one-based index

        Examples
        --------
        >>>WellPlate.name_to_index("A")
        1
        '''
        return ord(name) - 64

    @staticmethod
    def index_to_name(index):
        '''
        Translate row index to name.

        Parameters
        ----------
        index: int
            one-based index

        Returns
        -------
        str
            capital letter

        Examples
        --------
        >>>WellPlate.index_to_name(1)
        "A"
        '''
        return chr(index+64)

    @staticmethod
    def well_id_to_position(self, well_id):
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
        '''
        row_name, col_name = re.match(r'([A-Z])(\d{2})', well_id).group(1, 2)
        row_index = WellPlate.name_to_index(row_name)
        col_index = int(col_name)
        return (row_index, col_index)

    @staticmethod
    def well_position_to_id(well_position):
        '''
        Mapping of the one-based index position to the identifier string
        representation, e.g. (1, 2) -> "A02"

        Parameters
        ----------
        well_position: Tuple[int]
            one-based row, column position of a given well within the plate

        Returns
        -------
        str
            identifier string representation of a well
        '''
        row_index, col_index = well_position[0], well_position[1]
        row_name = WellPlate.index_to_name(row_index)
        return '%s%.2d' % (row_name, col_index)


class Slide(Cycle):

    def __init__(self, cycle_dir, cfg, user_cfg):
        '''
        Initialize an instance of class Slide.

        Parameters
        ----------
        cycle_dir: str
            absolute path to the cycle directory
        cfg: Dict[str, str]
            configuration settings
        user_cfg: Dict[str, str]
            additional user configuration settings
        '''
        super(Slide, self).__init__(cycle_dir, cfg, user_cfg)
        self.cycle_dir = os.path.abspath(cycle_dir)
        self.cfg = cfg
        self.user_cfg = user_cfg

    @property
    def dimensions(self):
        '''
        Returns
        -------
        Tuple[int]
            total number of rows and columns in the plate
        '''
        self._dimensions = (1, 1)
        return self._dimensions
