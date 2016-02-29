import numpy as np


def illum_correct_vips(orig_image, mean_mat, std_mat, log_transform=True):
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
        log10 transform `orig_image` (default: ``True``)

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
    img = (img - mean_mat) / std_mat
    img = img * std_mat.avg() + mean_mat.avg()
    if log_transform:
        img = 10 ** img

    # Cast back to original type
    return img.cast(orig_format)


def illum_correct_numpy(orig_image, mean_mat, std_mat, log_transform=True):
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
        log10 transform `orig_image` (default: ``True``)

    Returns
    -------
    numpy.ndarray
        corrected image (same data type as `orig_image`)
    '''
    img_type = orig_image.dtype

    # Do all computations with type float
    img = orig_image.astype(np.float64)
    img[img == 0] = 1
    if log_transform:
        img = np.log10(img)
    img = (img - mean_mat) / std_mat
    img = (img * np.mean(std_mat)) + np.mean(mean_mat)
    if log_transform:
        img = 10 ** img

    # Convert back to original type.
    return img.astype(img_type)
