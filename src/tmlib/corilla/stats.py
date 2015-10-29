'''
Calculation of illumination statistics, which can subsequently be applied
to individual images in order to correct them for illumination artifacts [1]_.

References
----------

.. _[1]: Stoeger T, Battich N, Herrmann MD, Yakimovich Y, Pelkmans L. 2015. "Computer vision for image-based transcriptomics". Methods.
'''


import numpy as np


class OnlineStatistics(object):

    '''
    Class for calculating online statistics based on Welford's method [1]_ .
    Code adapted from Wikipedia article "Algorithms for calculating variance"
    [2]_ .

    References
    ----------
    .. [1] B. P. Welford (1962). "Note on a method for calculating corrected sums of squares and products". Technometrics 4(3):419-420

    .. [2] https://en.wikipedia.org/wiki/Algorithms_for_calculating_variance#Online_algorithm
    '''

    def __init__(self, image_dimensions):
        '''
        Initialize class OnlineStatistics.

        Calculate online statistics (mean, variance, and standard deviation)
        element-by-element on a series of numpy arrays.

        Parameters
        ----------
        image_dimensions: Tuple[int]
            dimensions of the pixel array
        '''
        self.n = 0
        self.image_dimensions = image_dimensions
        self.mean = np.zeros(image_dimensions, dtype=float)
        self._M2 = np.zeros(image_dimensions, dtype=float)

    def update(self, x, log_transform=True):
        '''
        Update statistics with new matrix.

        Parameters
        ----------
        x: numpy.ndarray[float]
            new matrix
        log_transform: bool, optional
            log10 transform matrix (defaults to True)
        '''
        if not isinstance(x, np.ndarray):
            raise TypeError('data must be a numpy array')
        x = x.astype(float)
        if log_transform:
            x = np.log10(x)
        self.n = self.n + 1
        delta = x - self.mean
        self.mean = self.mean + delta/self.n
        self._M2 = self._M2 + delta*(x - self.mean)

    @property
    def var(self):
        '''
        Returns
        -------
        numpy.ndarray[float]
            variance
        '''
        if self.n < 2:
            self._var = np.zeros(self.image_dimensions, dtype=float)
            self._var[:] = np.nan
        else:
            self._var = self._M2 / (self.n - 1)
        return self._var

    @property
    def std(self):
        '''
        Returns
        -------
        numpy.ndarray[float]
            standard deviation
        '''
        self._std = np.sqrt(self.var)
        return self._std
