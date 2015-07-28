import h5py
import re
import numpy as np
import scipy.ndimage as ndi
from tmt.utils import regex_from_format_string
try:
    from gi.repository import Vips
except ImportError as error:
    print 'Vips could not be imported.\nReason: %s' % str(error)


def illum_correct_vips(orig_image, mean_mat, std_mat,
                       log_transform=True, smooth=False, sigma=5):
    '''
    Correct fluorescence microscopy image for illumination artifacts
    using the image processing library Vips.

    Parameters
    ----------
    orig_image: Vips.Image[Vips.BandFormat.USHORT]
        image that should be corrected
    mean_mat: Vips.Image[Vips.BandFormat.DOUBLE]
        matrix of mean values (same dimensions as `orig_image`)
    std_mat: Vips.Image[Vips.BandFormat.DOUBLE]
        matrix of standard deviation values (same dimensions as `orig_image`)
    log_transform: bool, optional
        log10 transform `orig_image` (defaults to True)
    smooth: bool, optional
        blur `mean_mat` and `std_mat` with a Gaussian filter (defaults to False)
    sigma: int, optional
        size of the standard deviation of the Gaussian kernel (defaults to 5)

    Returns
    -------
    Vips.Image
        corrected image (same data type as `orig_image`)
    '''
    # If we don't cast the conditional image, the result of ifthenelse
    # will be UCHAR
    orig_format = orig_image.get_format()
    cond = (orig_image == 0).cast(orig_format)
    img = cond.ifthenelse(1, orig_image)

    # Do all computations with double precision
    img = img.cast('double')
    if log_transform:
        img = img.log10()
    if smooth:
        mean_mat = mean_mat.gaussblur(sigma)
        std_mat = std_mat.gaussblur(sigma)
    img = (img - mean_mat) / std_mat
    img = img * std_mat.avg() + mean_mat.avg()
    if log_transform:
        img = 10 ** img

    # Cast back to UINT16 or whatever the original image was
    return img.cast(orig_format)


def illum_correct_numpy(orig_image, mean_mat, std_mat,
                        log_transform=True, smooth=True, sigma=5,
                        fix_pixels=False):
    '''
    Correct fluorescence microscopy image for illumination artifacts.

    Parameters
    ----------
    orig_image: numpy.ndarray
        image that should be corrected
    mean_mat: numpy.ndarray[numpy.float64]
        matrix of mean values (same dimensions as `orig_image`)
    std_mat: numpy.ndarray[numpy.float64]
        matrix of standard deviation values (same dimensions as `orig_image`)
    log_transform: bool, optional
        log10 transform `orig_image` (defaults to True)
    smooth: bool, optional
        blur `mean_mat` and `std_mat` with a Gaussian filter (defaults to False)
    sigma: int, optional
        standard deviation of the Gaussian kernel (defaults to 5)

    Returns
    -------
    numpy.ndarray
        corrected image (same data type as `orig_image`)
    '''
    # correct intensity image for illumination artifact
    img = orig_image.copy()
    img_type = orig_image.dtype
    img = img.astype(np.float64)
    img[img == 0] = 1
    if log_transform:
        img = np.log10(img)
    if smooth:
        mean_mat = ndi.filters.gaussian_filter(mean_mat, sigma)
        std_mat = ndi.filters.gaussian_filter(std_mat, sigma)
    img = (img - mean_mat) / std_mat
    img = (img * np.mean(std_mat)) + np.mean(mean_mat)
    if log_transform:
        img = 10 ** img

    if fix_pixels:
        # fix "bad" pixels with non numeric values (NaN or Inf)
        ix_bad = np.logical_not(np.isfinite(img))
        if ix_bad.sum() > 0:
            med_filt_image = ndi.filters.median_filter(img, 3)
            img[ix_bad] = med_filt_image[ix_bad]
            img[ix_bad] = med_filt_image[ix_bad]

        # fix extreme pixels
        percent = 99.9999
        thresh = np.percentile(img, percent)
        img[img > thresh] = thresh

    # TODO: is this save? Converting to integer values may lead to loss of
    # information, which would be a problem for values scaled between 0 and 1!
    return img.astype(img_type)


def illum_correct(orig_image, mean_mat, std_mat,
                  log_transform=True, smooth=False, sigma=5):
    '''
    Correct fluorescence microscopy image for illumination artifacts.

    Parameters
    ----------
    orig_image: numpy.ndarray or Vips.Image
        image that should be corrected
    mean_mat: numpy.ndarray[numpy.float64] or Vips.Image[Vips.BandFormat.DOUBLE]
        matrix of mean values (same dimensions as `orig_image`)
    std_mat: numpy.ndarray[numpy.float64] or Vips.Image[Vips.BandFormat.DOUBLE]
        matrix of standard deviation values (same dimensions as `orig_image`)
    log_transform: bool, optional
        log10 transform `orig_image` (defaults to True)
    smooth: bool, optional
        blur `mean_mat` and `std_mat` with a Gaussian filter (defaults to False)
    sigma: int, optional
        standard deviation of the Gaussian kernel (defaults to 5)
    
    Returns
    -------
    numpy.ndarray or Vips.Image
        corrected image (same data type as `orig_image`)

    See also
    --------
    illum_correct_numpy
    illum_correct_vips
    '''
    if isinstance(orig_image, np.ndarray):
        img = illum_correct_numpy(orig_image, mean_mat, std_mat,
                                  log_transform, smooth, sigma)
    else:
        img = illum_correct_vips(orig_image, mean_mat, std_mat,
                                 log_transform, smooth, sigma)
    return img


class Illumstats(object):
    '''
    Utility class for illumination correction statistics.

    It provides the mean and standard deviation images and the channel number.
    The statistics were calculated for each pixel position over all image sites
    acquired in the same channel [1]_.

    References
    ----------
    .. [1] Stoeger T, Battich N, Herrmann MD, Yakimovich Y, Pelkmans L. 2015.
           Computer vision for image-based transcriptomics. Methods.
    '''

    def __init__(self, filename, cfg, matlab=False):
        '''
        Initialize Illumstats class.

        Images are either `Vips` or `numpy`,
        depending on `USE_VIPS_LIBRARY` configuration.

        Parameters
        ----------
        filename: str
            path to the statistics file
        cfg: Dict[str, str]
            configuration settings
        matlab: bool, optional
            if statistics were calculated with Matlab
        '''
        self.cfg = cfg
        self.filename = filename
        self.matlab = matlab
        self.use_vips = self.cfg['USE_VIPS_LIBRARY']
        self.__statistics = None
        self._mean_image = None
        self._std_image = None
        self._channel = None

    @property
    def _statistics(self):
        if self.__statistics is None:
            stats = h5py.File(self.filename, 'r')
            stats = stats['stat_values']
            if self.use_vips:
                mean_image = Vips.Image.new_from_array(stats['mean'][()].tolist()).cast('double')
                std_image = Vips.Image.new_from_array(stats['std'][()].tolist()).cast('double')
            else:
                mean_image = np.array(stats['mean'][()], dtype='float64')
                std_image = np.array(stats['std'][()], dtype='float64')
                if self.matlab:
                    # Matlab transposes arrays when saving them to HDF5 files
                    # so we have to transpose them back!
                    mean_image = mean_image.conj().T
                    std_image = std_image.conj().T
            self.__statistics = (mean_image, std_image)
        return self.__statistics

    @property
    def channel(self):
        '''
        Returns
        -------
        int
            channel number
        '''
        if self._channel is None:
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
        numpy.ndarray[numpy.float64] or Vips.Image[Vips.BandFormat.DOUBLE]
            image matrix of mean values at each pixel position
            (statistic calculated at each pixel position over all image sites)
        '''
        if self._mean_image is None:
            self._mean_image = self._statistics[0]
        return self._mean_image

    @property
    def std_image(self):
        '''
        Returns
        -------
        numpy.ndarray[numpy.float64] or Vips.Image[Vips.BandFormat.DOUBLE]
            image matrix of standard deviation values
            (statistic calculated at each pixel position over all image sites)
        '''
        if self._std_image is None:
            self._std_image = self._statistics[1]
        return self._std_image

    def correct(self, image, smooth=False, sigma=5):
        '''
        Correct image for illumination artifacts.

        Parameters
        ----------
        image: numpy.ndarray or Vips.Image
            image that should be corrected
        smooth: bool, optional
            whether smoothing of statistics images should be performed
            prior to correction by applying a Gaussian kernel (defaults to False)
        sigma: int, optional
            size of the smoothing filter, i.e. standard deviation of the
            Gaussian kernel (defaults to 5)

        Returns
        -------
        numpy.ndarray or Vips.Image
            corrected image
        '''
        corrected_image = illum_correct(image, self.mean_image, self.std_image)
        return corrected_image
