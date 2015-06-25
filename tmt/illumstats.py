import h5py
import re
import numpy as np
import scipy.ndimage as ndi
from tmt.imageutil import np_array_to_vips_image
from tmt.util import regex_from_format_string


def illum_correction_vips(orig_image, mean_image, std_image):
    '''
    Correct fluorescence microscopy image for illumination artifacts
    using the image processing library Vips.

    Parameters
    ----------
    orig_image: Vips.Image[Vips.BandFormat.USHORT]
        image that should be corrected
    mean_image: Vips.Image[Vips.BandFormat.DOUBLE]
        matrix of mean values (same dimensions as `orig_image`)
    std_image: Vips.Image[Vips.BandFormat.DOUBLE]
        matrix of standard deviation values (same dimensions as `orig_image`)

    Returns
    -------
    Vips.Image[Vips.BandFormat.USHORT]
        corrected image
    '''
    # If we don't cast the conditional image, the result of ifthenelse
    # will be UCHAR
    orig_format = orig_image.get_format()
    cond = (orig_image == 0).cast(orig_format)
    img = cond.ifthenelse(1, orig_image)

    # Do all computations with double precision
    img = img.cast('double')
    img = img.log10()
    img = (img - mean_image) / std_image
    img = img * std_image.avg() + mean_image.avg()
    img = 10 ** img

    # Cast back to UINT16 or whatever the original image was
    img = img.cast(orig_format)

    return img


def illum_correction(orig_image, mean_mat, std_mat, fix_pixels=False):
    """
    Correct fluorescence microscopy image for illumination artifacts.

    Parameters
    ----------
    orig_image: numpy.ndarray[numpy.uint16]
        image that should be corrected
    mean_mat: numpy.ndarray[numpy.float64]
        matrix of mean values (same dimensions as `orig_image`)
    std_mat: numpy.ndarray[numpy.float64]
        matrix of standard deviation values (same dimensions as `orig_image`)
    
    Returns
    -------
    numpy.ndarray[numpy.uint16]
        corrected image
    """
    # correct intensity image for illumination artifact
    img = orig_image.copy()
    img = img.astype(np.float64)
    img[img == 0] = 1
    img = (np.log10(img) - mean_mat) / std_mat
    img = (img * np.mean(std_mat)) + np.mean(mean_mat)
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

    return img.astype(np.uint16)


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
        self._statistics = None
        self._mean_image = None
        self._std_image = None
        self._channel = None

    @property
    def _statistics(self):
        if not self._statistics:
            stats = h5py.File(self.filename, 'r')
            stats = stats['stat_values']
            mean_image = np.array(stats['mean'][()], dtype='float64')
            std_image = np.array(stats['std'][()], dtype='float64')
            if self.matlab:
                # Matlab transposes arrays when saving them to HDF5 files
                # so we have to transpose them back!
                mean_image = mean_image.conj().T
                std_image = std_image.conj().T
            if self.use_vips:
                mean_image = np_array_to_vips_image(mean_image)
                std_image = np_array_to_vips_image(std_image)
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
        numpy.ndarray[numpy.float64] or Vips.Image[Vips.BandFormat.DOUBLE]
            image matrix of mean values at each pixel position
            (statistic calculated at each pixel position over all image sites)
        '''
        if not self._mean_image:
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
        if not self._std_image:
            self._std_image = self._statistics[1]
        return self._std_image

    def correct_illumination(self, image):
        '''
        Correct image for illumination artifacts.

        Parameters
        ----------
        image: numpy.ndarray or Vips.Image
            image that should be corrected

        Returns
        -------
        numpy.ndarray[numpy.unit16] or Vips.Image[Vips.BandFormat.USHORT]
            corrected image
        '''
        if self.use_vips:
            img = illum_correction_vips(image, self.mean_image, self.std_image)
        else:
            img = illum_correction(image, self.mean_image, self.std_image)

        return img
