import numpy as np


class OnlineStatistics(object):

    '''
    Class for calculating online statistics based on Welford's method:

    B. P. Welford (1962). "Note on a method for calculating corrected sums of
    squares and products". Technometrics 4(3):419-420.

    Code adapted from Wikipedia article "Algorithms for calculating variance".
    https://en.wikipedia.org/wiki/Algorithms_for_calculating_variance
    '''

    def __init__(self, dims):
        '''
        Initiate class OnlineStatistics.

        Calculate online statistics (mean, variance, and standard deviation)
        element-by-element on a series of numpy arrays.

        Parameters
        ----------
        dims: Tuple[int]
              dimensions (i.e. shape) of a numpy array
        '''
        self.n = 0
        self.dims = dims
        self.mean = np.zeros(dims, dtype=float)
        self.M2 = np.zeros(dims, dtype=float)

    def update(self, x):
        '''
        Parameters
        ----------
        x: numpy.ndarray[float]
        '''
        if not isinstance(x, np.ndarray):
            raise TypeError('data must be a numpy array')
        if x.dtype != np.float:
            raise TypeError('data type must be float')
        self.n = self.n + 1
        delta = x - self.mean
        self.mean = self.mean + delta/self.n
        self.M2 = self.M2 + delta*(x - self.mean)

    @property
    def var(self):
        '''
        Returns
        -------
        numpy.ndarray[float]
        variance
        '''
        if self.n < 2:
            self._var = np.zeros(self.dims, dtype=float)
            self._var[:] = np.nan
        else:
            self._var = self.M2 / (self.n - 1)
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
