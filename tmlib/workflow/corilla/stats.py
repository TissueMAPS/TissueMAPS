# TmLibrary - TissueMAPS library for distibuted image analysis routines.
# Copyright (C) 2016  Markus D. Herrmann, University of Zurich and Robin Hafen
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''Calculation of illumination statistics, which can subsequently be applied
to individual images in order to correct them for illumination artifacts [1] .

References
----------
.. [1] Stoeger T, Battich N, Herrmann MD, Yakimovich Y, Pelkmans L. 2015. "Computer vision for image-based transcriptomics". Methods.
.. [2] Welford BP. 1962. "Note on a method for calculating corrected sums of squares and products". Technometrics 4(3):419-420.

'''

import numpy as np
import logging

from tmlib.utils import assert_type
from tmlib.image import IllumstatsImage

logger = logging.getLogger(__name__)


class OnlineStatistics(object):

    '''Class for calculating online statistics (mean and variance)
    element-by-element on a series of numpy arrays based on
    Welford's method [2] . For more information see Wikipedia article
    `"Algorithms for calculating variance" <https://en.wikipedia.org/wiki/Algorithms_for_calculating_variance#Online_algorithm>`_.
    '''

    def __init__(self, image_dimensions, decimals=3):
        '''
        Parameters
        ----------
        image_dimensions: Tuple[int]
            dimensions of the pixel array
        decimals: int
            precision after the comma that determines the number of percentiles
            that will be calculated
        '''
        self.n = 0
        self.image_dimensions = image_dimensions
        self._mean = np.zeros(image_dimensions, dtype=float)
        self._M2 = np.zeros(image_dimensions, dtype=float)
        if not(0 <= decimals <= 3):
            raise ValueError('Argument "decimals" must lie in range [0, 3].')
        precision = 10**(decimals+2)
        self._q = np.linspace(0, 100, precision)
        self._percentiles = np.zeros((precision, ), dtype=np.float)
        self._keys = [round(x, decimals) for x in self._q]

    @assert_type(image='tmlib.image.ChannelImage')
    def update(self, image, log_transform=True):
        '''Update statistics with additional image.

        Parameters
        ----------
        image: tmlib.image.ChannelImage
            additional image
        log_transform: bool, optional
            log10 transform image (default: ``True``)
        '''
        # Calculate percentiles with unsigned integer data type
        self._percentiles += np.percentile(image.array, self._q)
        # The other statistics require float data type
        array = image.array.astype(float)
        if log_transform:
            is_zero = array == 0
            if np.any(is_zero):
                logger.warn('image contains zero values')
            array = np.log10(array)
            # The log10 transform sets zero pixel values to -inf
            array[is_zero] = 0
        if np.any(np.isinf(array)):
            logger.warn('skip image because it contains infinite values')
        else:
            self.n += 1
            delta_mean = (array - self._mean).astype(np.float32)
            try:
                # update self._mean by memory efficiency in-place operations
                norm_delta_mean = np.array(delta_mean, copy=True)
                norm_delta_mean /= self.n
                self._mean += norm_delta_mean
            except Exception as ex:
                raise MemoryError(
                    "unsufficiant memory available for updating "
                    "online statistics"
                )
            self._M2 = self._M2 + delta_mean * (array - self._mean)

    @property
    def var(self):
        '''numpy.ndarray[float]: variance'''
        if self.n < 2:
            var = np.zeros(self.image_dimensions, dtype=float)
            var[:] = np.nan
        else:
            var = self._M2 / (self.n - 1)
        return var

    @property
    def mean(self):
        '''tmlib.image.IllumstatsImage: mean values'''
        return IllumstatsImage(self._mean)

    @property
    def std(self):
        '''tmlib.image.IllumstatsImage: standard deviation values'''
        return IllumstatsImage(np.sqrt(self.var))

    @property
    def percentiles(self):
        '''Dict[float, int]: calculated percentiles (rounded to integer values)
        '''
        return {
            self._keys[i]: int(x/self.n)
            for i, x in enumerate(self._percentiles)
        }
