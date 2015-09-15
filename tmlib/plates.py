import os
import re
# import numpy as np
from .cycle import Cycle
# from .layers import ChannelLayer
# from .layers import MaskLayer
# from .layers import LabelLayer
# from .layers import BrightfieldLayer
# from .errors import NotSupportedError


class WellPlate(Cycle):

    def __init__(self, cycle_dir, cfg, plate_format):
        '''
        Initialize an instance of class WellPlate.

        Parameters
        ----------
        cycle_dir: str
            absolute path to the cycle directory
        cfg: Dict[str, str]
            configuration settings
        plate_format: int
            number of wells in the plate (supported: 96 or 384)
        '''
        super(WellPlate, self).__init__(cycle_dir, cfg)
        self.cycle_dir = os.path.abspath(cycle_dir)
        self.cfg = cfg
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
    def well_positions(self):
        '''
        Returns
        -------
        List[Tuple[int]]
            one-based row, column position of each well in the plate
        '''
        self._well_positions = set([self.id_to_position(w)
                                    for w in self.well_ids])
        return self._well_positions

    @property
    def well_ids(self):
        '''
        Returns
        -------
        str
            well identifier string: capital letter for row position and
            number for column position
        '''
        self._well_ids = [md.well for md in self.image_metadata]
        return self._well_ids

    @property
    def n_wells(self):
        '''
        Returns
        -------
        int
            number of wells in plate
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

    # @property
    # def channel_layers(self):
    #     '''
    #     Returns
    #     -------
    #     Dict[Tuple, List[ChannelLayer]]
    #         grid of grayscale images for each channel at each well position

    #     See also
    #     --------
    #     `layers.ChannelLayer`_
    #     '''
    #     # group images per well
    #     image_data = zip(self.image_files, self.image_metadata)
    #     self._channel_layers = dict()
    #     for w in self.wells:
    #         well_data = [(f, m) for f, m in image_data if m.well == w]
    #         self._channel_layers[w] = list()
    #         # further subgroup images per channel
    #         for c in self.channels:
    #             channel_data = np.array([(f, m) for f, m in well_data
    #                                      if m.channel == c])
    #             self._channel_layers[w].append(
    #                             ChannelLayer(image_files=channel_data[:, 0],
    #                                          metadata=channel_data[:, 1]))
    #     return self._channel_layers

    # @property
    # def mask_layers(self):
    #     '''
    #     Returns
    #     -------
    #     Dict[Tuple, List[MaskLayer]]
    #         grid of binary images for each object type at each well position

    #     See also
    #     --------
    #     `layers.MaskLayer`_
    #     '''
    #     if self.segmentation_files:
    #         # group images per well
    #         segm_data = zip(self.segmentation_files,
    #                         self.segmentation_metadata)
    #         self._mask_layers = dict()
    #         for w in self.wells:
    #             well_data = [(f, m) for f, m in segm_data if m.well == w]
    #             self._mask_layers[w] = list()
    #             # further subgroup images per object type
    #             for o in self.objects:
    #                 object_data = np.array([(f, m) for f, m in well_data
    #                                         if m.objects == o])
    #                 self._mask_layers[w].append(
    #                             MaskLayer(image_files=object_data[:, 0],
    #                                       metadata=object_data[:, 1],
    #                                       data_file=self.data_file))
    #     else:
    #         self._mask_layers = {}
    #     return self._mask_layers

    # @property
    # def label_layers(self):
    #     '''
    #     Returns
    #     -------
    #     Dict[Tuple, List[LabelLayer]]
    #         grid of RGB images for each object type at each well position

    #     See also
    #     --------
    #     `layers.LabelLayer`_
    #     '''
    #     if self.segmentation_files:
    #         # group images per well
    #         segm_data = zip(self.segmentation_files,
    #                         self.segmentation_metadata)
    #         self._label_layers = dict()
    #         for w in self.wells:
    #             well_data = [(f, m) for f, m in segm_data if m.well == w]
    #             self._label_layers[w] = list()
    #             # further subgroup images per object type
    #             for o in self.objects:
    #                 object_data = np.array([(f, m) for f, m in well_data
    #                                         if m.objects == o])
    #                 self._label_layers[w].append(
    #                             LabelLayer(image_files=object_data[:, 0],
    #                                        metadata=object_data[:, 1],
    #                                        data_file=self.data_file))
    #     else:
    #         self._label_layers = {}
    #     return self._label_layers

    # @property
    # def brightfield_layers(self):
    #     '''
    #     Raises
    #     ------
    #     NotSupportedError
    #         since brightfield mode is not supported for well plate formats
    #     '''
    #     raise NotSupportedError('Brightfield mode is not supported '
    #                             'for well plates')


class Slide(Cycle):

    def __init__(self, cycle_dir, cfg):
        '''
        Initialize an instance of class Slide.

        Parameters
        ----------
        cycle_dir: str
            absolute path to the cycle directory
        cfg: Dict[str, str]
            configuration settings
        '''
        super(Slide, self).__init__(cycle_dir, cfg)
        self.cycle_dir = os.path.abspath(cycle_dir)
        self.cfg = cfg

    # @property
    # def mask_layers(self):
    #     '''
    #     Returns
    #     -------
    #     List[MaskLayer]
    #         grid of binary images for each object type

    #     See also
    #     --------
    #     `layers.MaskLayer`_
    #     '''
    #     if self.segmentation_files:
    #         # group images per object type
    #         segm_data = zip(self.segmentation_files,
    #                         self.segmentation_metadata)
    #         self.mask_layers = list()
    #         # further subgroup images per object type
    #         for o in self.objects:
    #             object_data = np.array([(f, m) for f, m in segm_data
    #                                     if m.objects == o])
    #             self.mask_layers.append(
    #                         MaskLayer(image_files=object_data[:, 0],
    #                                   metadata=object_data[:, 1],
    #                                   data_file=self.data_file))
    #     else:
    #         self._mask_layers = {}
    #     return self.mask_layers

    # @property
    # def label_layers(self):
    #     '''
    #     Returns
    #     -------
    #     List[LabelLayer]
    #         grid of RGB images for each object type

    #     See also
    #     --------
    #     `layers.LabelLayer`_
    #     '''
    #     if self.segmentation_files:
    #         # group images per object type
    #         segm_data = zip(self.segmentation_files,
    #                         self.segmentation_metadata)
    #         self.mask_layers = list()
    #         # further subgroup images per object type
    #         for o in self.objects:
    #             object_data = np.array([(f, m) for f, m in segm_data
    #                                     if m.objects == o])
    #             self.mask_layers.append(
    #                         LabelLayer(image_files=object_data[:, 0],
    #                                    metadata=object_data[:, 1],
    #                                    data_file=self.data_file))
    #     else:
    #         self._mask_layers = {}
    #     return self.mask_layers


class FluorescenceSlide(Slide):

    '''
    Class for a fluorescent slide, which has one or more grayscale layers
    (channels).
    '''

    def __init__(self, cycle_dir, cfg):
        '''
        Initialize an instance of class FluorescenceSlide.

        Parameters
        ----------
        cycle_dir: str
            absolute path to the cycle directory
        cfg: Dict[str, str]
            configuration settings
        '''
        super(FluorescenceSlide, self).__init__(cycle_dir, cfg)
        self.cycle_dir = os.path.abspath(cycle_dir)
        self.cfg = cfg

    # @property
    # def channel_layers(self):
    #     '''
    #     Returns
    #     -------
    #     List[ChannelLayer]
    #         grid of grayscale images for each channel

    #     See also
    #     --------
    #     `layers.ChannelLayer`_
    #     '''
    #     # group images per channel
    #     image_data = zip(self.image_files,
    #                      self.image_metadata)
    #     self._channel_layers = list()
    #     for c in self.channels:
    #         channel_data = np.array([(f, m) for f, m in image_data
    #                                  if m.channel == c])
    #         self._channel_layers.append(
    #                     ChannelLayer(image_files=channel_data[:, 0],
    #                                  metadata=channel_data[:, 1]))
    #     return self._channel_layers


class BrightfieldSlide(Slide):

    '''
    Class for a brightfield slide, which has only one RGB layer.
    '''

    def __init__(self, cycle_dir, cfg):
        '''
        Initialize an instance of class BrightfieldSlide.

        Parameters
        ----------
        cycle_dir: str
            absolute path to the cycle directory
        cfg: Dict[str, str]
            configuration settings
        '''
        super(BrightfieldSlide, self).__init__(cycle_dir, cfg)
        self.cycle_dir = os.path.abspath(cycle_dir)
        self.cfg = cfg

    # @property
    # def brightfield_layer(self):
    #     '''
    #     Returns
    #     -------
    #     BrightfieldLayer
    #         grid of RGB images

    #     See also
    #     --------
    #     `layers.BrightfieldLayer`_
    #     '''
    #     self._brightfield_layer = BrightfieldLayer(self.image_files[0])
    #     return self._brightfield_layer
