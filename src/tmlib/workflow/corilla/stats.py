'''
Calculation of illumination statistics, which can subsequently be applied
to individual images in order to correct them for illumination artifacts [1]_.

References
----------

.. _[1]: Stoeger T, Battich N, Herrmann MD, Yakimovich Y, Pelkmans L. 2015. "Computer vision for image-based transcriptomics". Methods.
'''


import numpy as np


class OnlineStatistics(object):

    '''Class for calculating online statistics (mean and variance)
    element-by-element on a series of numpy arrays based on
    Welford's method [1]_ . For more information see Wikipedia article
    "Algorithms for calculating variance" [2]_ .

    References
    ----------
    .. [1] B. P. Welford (1962). "Note on a method for calculating corrected sums of squares and products". Technometrics 4(3):419-420

    .. [2] https://en.wikipedia.org/wiki/Algorithms_for_calculating_variance#Online_algorithm
    '''

    def __init__(self, image_dimensions):
        '''
        Parameters
        ----------
        image_dimensions: Tuple[int]
            dimensions of the pixel array
        '''
        self.n = 0
        self.image_dimensions = image_dimensions
        self.mean = np.zeros(image_dimensions, dtype=float)
        self._M2 = np.zeros(image_dimensions, dtype=float)

    def update(self, image, log_transform=True):
        '''Update statistics with additional image.

        Parameters
        ----------
        image: numpy.ndarray[numpy.uint16]
            additional image
        log_transform: bool, optional
            log10 transform image (default: ``True``)

        Raises
        ------
        TypeError
            when `image` doesn't have type `numpy.ndarray`
        '''
        if not isinstance(image, np.ndarray):
            raise TypeError('Image must be a numpy array.')
        image = image.astype(float)
        if log_transform:
            image = np.log10(image)
        self.n += 1
        delta_mean = image - self.mean
        self.mean = self.mean + delta_mean / self.n
        self._M2 = self._M2 + delta_mean * (image - self.mean)

    @property
    def var(self):
        '''numpy.ndarray[float]: variance'''
        if self.n < 2:
            self._var = np.zeros(self.image_dimensions, dtype=float)
            self._var[:] = np.nan
        else:
            self._var = self._M2 / (self.n - 1)
        return self._var

    @property
    def std(self):
        '''numpy.ndarray[float]: standard deviation'''
        self._std = np.sqrt(self.var)
        return self._std


class OnlinePercentile(object):

    '''Class for calculating online percentiles on a series of numpy arrays.

    The calculated percentiles can be used to rescale intensity values of
    images for better display, for example.
    '''

    def __init__(self, decimals=3):
        '''
        Parameters
        ----------
        decimals: int
            precision after the comma that determines the number of percentiles
            that will be calculated
        '''
        if not(0 <= decimals <= 3):
            raise ValueError('Argument "decimals" must lie in range [0, 3].')
        precision = 10**(decimals+2)
        self.n = 0
        self.q = np.linspace(0, 100, precision)
        self._percentiles = np.empty((precision, ), dtype=np.float)
        self._keys = [round(x, 3) for x in self.q]

    def update(self, image):
        '''Update percentile with additional image.

        Parameters
        ----------
        image: numpy.ndarray[numpy.uint16]
            additional image

        Raises
        ------
        TypeError
            when `image` doesn't have type `numpy.ndarray`
        '''
        if not isinstance(image, np.ndarray):
            raise TypeError('Image must be a numpy array.')
        self.n += 1
        self._percentiles += np.percentile(image, self.q)

    @property
    def percentiles(self):
        '''
        Returns
        -------
        int
            calculated percentiles (rounded to integer values)
        '''
        return {
            self._keys[i]: int(x/self.n)
            for i, x in enumerate(self._percentiles)
        }
