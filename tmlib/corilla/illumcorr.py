import numpy as np
import scipy.ndimage as ndi


def illum_correct_vips(orig_image, mean_mat, std_mat,
                       log_transform=True, smooth=True, sigma=5):
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
                        log_transform=True, smooth=True, sigma=5):
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
    img = orig_image.copy()
    img_type = orig_image.dtype

    # Do all computations with type float
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

    # Convert back to original type.
    return img.astype(img_type)
