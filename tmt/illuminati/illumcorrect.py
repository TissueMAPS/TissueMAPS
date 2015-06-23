import numpy as np
import scipy.ndimage as ndi

# TODO: move this functionality into Illumstats class


def illum_correction_vips(orig_image, mean_image, std_image):
    '''
    Correct fluorescence microscopy image for illumination artifacts
    using the image processing library Vips.

    Parameters
    ----------
    orig_image: gi.overrides.Vips.Image[gi.overrides.Vips.BandFormat.DOUBLE]
                image that should be corrected
    mean_image: gi.overrides.Vips.Image[gi.overrides.Vips.BandFormat.DOUBLE]
                matrix of pre-calculated mean values
                (same dimensions as orig_image)
    std_image: gi.overrides.Vips.Image[gi.overrides.Vips.BandFormat.DOUBLE]
               matrix of pre-calculated standard deviation values
               (same dimensions as orig_image)

    Returns
    -------
    gi.overrides.Vips.Image[gi.overrides.Vips.BandFormat.DOUBLE]
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


def illum_correction(orig_image, mean_mat, std_mat):
    """
    Correct fluorescence microscopy image for illumination artifacts.

    Parameters
    ----------
    orig_image: numpy.ndarray[numpy.float64]
                image that should be corrected
    mean_mat: numpy.ndarray[numpy.float64]
              matrix of pre-calculated mean values
              (same dimensions as orig_image)
    std_mat: numpy.ndarray[numpy.float64]
             matrix of pre-calculated standard deviation values
             (same dimensions as orig_image)
    
    Returns
    -------
    numpy.ndarray[numpy.float64]
    corrected image
    """
    # correct intensity image for illumination artifact
    corr_image = orig_image.copy()
    corr_image[corr_image == 0] = 1
    corr_image = (np.log10(corr_image) - mean_mat) / std_mat
    corr_image = (corr_image * np.mean(std_mat)) + np.mean(mean_mat)
    corr_image = 10 ** corr_image

    # fix "bad" pixels with non numeric values (NaN or Inf)
    ix_bad = np.logical_not(np.isfinite(corr_image))
    if ix_bad.sum() > 0:
        med_filt_image = ndi.filters.median_filter(corr_image, 3)
        corr_image[ix_bad] = med_filt_image[ix_bad]
        corr_image[ix_bad] = med_filt_image[ix_bad]

    # fix extreme pixels
    percent = 99.9999
    thresh = np.percentile(corr_image, percent)
    corr_image[corr_image > thresh] = thresh

    return corr_image.astype(np.uint16)
