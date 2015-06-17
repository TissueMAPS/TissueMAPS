import h5py
import re
import numpy as np
from tmt.util import regex_from_format_string


class Illumstats:
    '''Utility class for an illumination correction statistics file.
    The class provides the mean and standard deviation image,
    which were precalculated across all images acquired in the same channel,
    and the corresponding channel number.
    '''

    def __init__(self, filename, cfg):
        '''
        Initialize Illumstats class.

        Parameters:
        :filename:      Path to the statistics file : str.
        :cfg:           Configuration settings : dict.
        '''
        self.cfg = cfg
        self.filename = filename
        self._statistics = None
        self._mean_image = None
        self._std_image = None
        self._channel = None

    @property
    def statistics(self):
        '''
        Load precomputed statistics and return mean and standard deviation
        images as a tuple of numpy arrays.

        By default the statistics files are HDF5 files
        with the following structure:
        /stat_values            Group
        /stat_values/mean       Dataset
        /stat_values/std        Dataset
        '''
        if not self._statistics:
            stats = h5py.File(self.filename, 'r')
            stats = stats['stat_values']
            # Matlab transposes arrays when saving them to HDF5 files
            # so we have to transpose them back!
            mean_image = np.array(stats['mean'][()], dtype='float64').conj().T
            std_image = np.array(stats['std'][()], dtype='float64').conj().T
            self._statistics = (mean_image, std_image)
        return self._statistics

    @property
    def channel(self):
        if not self._channel:
            regexp = regex_from_format_string(self.cfg['STATS_FILE_FORMAT'])
            m = re.search(regexp, self.filename)
            if not m:
                raise Exception('Can\'t determine channel from '
                                'illumination statistics file "%s"'
                                % self.filename)
            self._channel = int(m.group('channel'))
        return self._channel

    @property
    def mean_image(self):
        if not self._mean_image:
            self._mean_image = self._statistics[0]
        return self._mean_image

    @property
    def std_image(self):
        if not self._std_image:
            self._std_image = self._statistics[1]
        return self._std_image
