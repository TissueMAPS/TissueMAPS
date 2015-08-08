import os
import re
import numpy as np
from cycle import Cycle
from layers import ChannelLayer
from layers import MaskLayer
from layers import LabelLayer
from layers import BrightfieldLayer


class WellPlate(Cycle):

    '''
    Class that serves as a container for layers.

    A layer represents an acquisition grid, i.e. a continuous image
    acquisition area. In case of a well plate, layers are grouped by well.
    '''

    def __init__(self, cycle_dir, cfg, n_wells):
        '''
        Initialize an instance of class WellPlate.

        Parameters
        ----------
        cycle_dir: str
            absolute path to the cycle directory
        cfg: Dict[str, str]
            configuration settings
        n_wells: int
            number of wells in the plate (supported: 96 or 384)
        '''
        Cycle.__init__(cycle_dir, cfg)
        self.cycle_dir = os.path.abspath(cycle_dir)
        self.cfg = cfg
        self.n_wells = n_wells

    @property
    def dimensions(self):
        '''
        Returns
        -------
        Tuple[int]
            total number of rows and columns in the plate
        '''
        if self.n_wells == 96:
            self._dimensions = (8, 12)
        elif self.n_wells == 384:
            self._dimensions = (16, 24)
        return self._dimensions

    @property
    def well_positions(self):
        '''
        Returns
        -------
        List[Tuple[int]]
            zero-based row, column position of each well in the plate
        '''
        self._well_positions = set([m.well_position
                                    for m in self.image_metadata])
        return self._well_positions

    @property
    def n_wells(self):
        '''
        Returns
        -------
        int
            number of wells in plate
        '''
        self._n_wells = len(set(self._wells))
        return self._n_wells

    def map_well_position_to_id(self, well_id):
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
        row = ord(row_name) - 64  # needs to be a capital letter!
        col = int(col_name)
        return (row, col)

    @property
    def map_to_well_id_to_position(self, well_position):
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
        # TODO
        return self._map_to_well_id

    @property
    def well_ids(self):
        '''
        Returns
        -------
        str
            well identifier string: capital letter for row position and
            number for column position
        '''
        self._well_ids = [self.map_well_position_to_id(w) for w in self.wells]
        return self._well_ids

    @property
    def channel_layers(self):
        '''
        Returns
        -------
        Dict[Tuple, List[ChannelLayer]]
            grid of grayscale images for each channel at each well position

        See also
        --------
        `layers.ChannelLayer`_
        '''
        # group images per well
        image_data = zip(self.image_files,
                         self.image_metadata)
        self._channel_layers = dict()
        for w in self.wells:
            well_data = [(f, m) for f, m in image_data if m.well == w]
            self._channel_layers[w] = list()
            # further subgroup images per channel
            for c in self.channels:
                channel_data = np.array([(f, m) for f, m in well_data
                                         if m.channel == c])
                self._channel_layers[w].append(
                                ChannelLayer(image_files=channel_data[:, 0],
                                             metadata=channel_data[:, 1]))
        return self._channel_layers

    @property
    def mask_layers(self):
        '''
        Returns
        -------
        Dict[Tuple, List[MaskLayer]]
            grid of binary images for each object type at each well position

        See also
        --------
        `layers.MaskLayer`_
        '''
        if self.segmentation_files:
            # group images per well
            segm_data = zip(self.segmentation_files,
                            self.segmentation_metadata)
            self._mask_layers = dict()
            for w in self.wells:
                well_data = [(f, m) for f, m in segm_data if m.well == w]
                self._mask_layers[w] = list()
                # further subgroup images per object type
                for o in self.objects:
                    object_data = np.array([(f, m) for f, m in well_data
                                            if m.objects == o])
                    self._mask_layers[w].append(
                                MaskLayer(image_files=object_data[:, 0],
                                          metadata=object_data[:, 1],
                                          data_file=''))
        else:
            self._mask_layers = {}
        return self._mask_layers

    @property
    def label_layers(self):
        '''
        Returns
        -------
        Dict[Tuple, List[LabelLayer]]
            grid of RGB images for each object type at each well position

        See also
        --------
        `layers.LabelLayer`_
        '''
        if self.segmentation_files:
            # group images per well
            segm_data = zip(self.segmentation_files,
                            self.segmentation_metadata)
            self._label_layers = dict()
            for w in self.wells:
                well_data = [(f, m) for f, m in segm_data if m.well == w]
                self._label_layers[w] = list()
                # further subgroup images per object type
                for o in self.objects:
                    object_data = np.array([(f, m) for f, m in well_data
                                            if m.objects == o])
                    self._label_layers[w].append(
                                LabelLayer(image_files=object_data[:, 0],
                                           metadata=object_data[:, 1],
                                           data_file=''))
        else:
            self._label_layers = {}
        return self._label_layers

    @property
    def brightfield_layers(self):
        '''
        Raises
        ------
        NotImplementedError
            since brightfield mode is not supported for well plate formats
        '''
        raise NotImplementedError('Brightfield mode is not supported '
                                  'for well plates')


class Slide(Cycle):

    '''
    Class that serves as a container for layers.

    A layer represents an acquisition grid, i.e. a continuous image
    acquisition area.
    '''

    def __init__(self, cycle_dir, cfg):
        '''
        Initialize an instance of class WellPlate.

        Parameters
        ----------
        cycle_dir: str
            absolute path to the cycle directory
        cfg: Dict[str, str]
            configuration settings
        '''
        Cycle.__init__(cycle_dir, cfg)
        self.cycle_dir = os.path.abspath(cycle_dir)
        self.cfg = cfg

    @property
    def channel_layers(self):
        '''
        Returns
        -------
        List[ChannelLayer]
            grid of grayscale images for each channel

        See also
        --------
        `layers.ChannelLayer`_
        '''
        # group images per channel
        image_data = zip(self.image_files,
                         self.image_metadata)
        self._channel_layers = list()
        for c in self.channels:
            channel_data = np.array([(f, m) for f, m in image_data
                                     if m.channel == c])
            self._channel_layers.append(
                        ChannelLayer(image_files=channel_data[:, 0],
                                     metadata=channel_data[:, 1]))
        return self._channel_layers

    @property
    def mask_layers(self):
        '''
        Returns
        -------
        List[MaskLayer]
            grid of binary images for each object type

        See also
        --------
        `layers.MaskLayer`_
        '''
        if self.segmentation_files:
            # group images per object type
            segm_data = zip(self.segmentation_files,
                            self.segmentation_metadata)
            self.mask_layers = list()
            # further subgroup images per object type
            for o in self.objects:
                object_data = np.array([(f, m) for f, m in segm_data
                                        if m.objects == o])
                self.mask_layers.append(
                            MaskLayer(image_files=object_data[:, 0],
                                      metadata=object_data[:, 1],
                                      data_file=''))
        else:
            self._mask_layers = {}
        return self.mask_layers

    @property
    def label_layers(self):
        '''
        Returns
        -------
        List[LabelLayer]
            grid of RGB images for each object type

        See also
        --------
        `layers.LabelLayer`_
        '''
        if self.segmentation_files:
            # group images per object type
            segm_data = zip(self.segmentation_files,
                            self.segmentation_metadata)
            self.mask_layers = list()
            # further subgroup images per object type
            for o in self.objects:
                object_data = np.array([(f, m) for f, m in segm_data
                                        if m.objects == o])
                self.mask_layers.append(
                            LabelLayer(image_files=object_data[:, 0],
                                       metadata=object_data[:, 1],
                                       data_file=''))
        else:
            self._mask_layers = {}
        return self.mask_layers

    @property
    def brightfield_layer(self):
        '''
        Returns
        -------
        BrightfieldLayer
            grid of RGB images

        See also
        --------
        `layers.BrightfieldLayer`_
        '''
        # TODO
        return self._brightfield_layers
    
