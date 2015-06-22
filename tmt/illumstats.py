import h5py
import re
import numpy as np
from tmt.util import regex_from_format_string


class Illumstats:
    '''
    Utility class for illumination correction statistics.

    It provides the mean and standard deviation images and the channel number.
    The statistics were calculated for each pixel position over all image sites
    acquired in the same channel.

    Reference
    ---------
    Battich et al. 2015 Methods
    '''

    def __init__(self, filename, cfg):
        '''
        Initiate Illumstats class.

        Parameters
        ----------
        filename: str
                  path to the statistics file
        cfg: Dict[str, str]
             configuration settings
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
        Load precomputed statistics and return mean and std images.

        By default the statistics files are HDF5 files
        with the following structure:
        /stat_values            Group
        /stat_values/mean       Dataset
        /stat_values/std        Dataset

        Returns
        -------
        Tuple[ndarray]
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
        '''
        Returns
        -------
        int
        channel number
        '''
        if not self._channel:
            regexp = regex_from_format_string(self.cfg['STATS_FILE_FORMAT'])
            m = re.search(regexp, self.filename)
            if not m:
                raise ValueError('Can\'t determine channel from '
                                 'illumination statistics file "%s"'
                                 % self.filename)
            self._channel = int(m.group('channel'))
        return self._channel

    @property
    def mean_image(self):
        '''
        Returns
        -------
        ndarray
        image matrix of mean values at each pixel position
        (statistic pre-calculated at each pixel position over all image sites)
        '''
        if not self._mean_image:
            self._mean_image = self._statistics[0]
        return self._mean_image

    @property
    def std_image(self):
        '''
        Returns
        -------
        ndarray
        image matrix of standard deviation values
        (statistic pre-calculated at each pixel position over all image sites)
        '''
        if not self._std_image:
            self._std_image = self._statistics[1]
        return self._std_image
