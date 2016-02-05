'''Utility functions for common image processing routines.'''

import random as rand
from gi.repository import Vips
from scipy.misc import imread, bytescale
import numpy as np
import logging
from skimage.exposure import rescale_intensity

logger = logging.getLogger(__name__)


def np_dtype_to_vips_format(np_dtype):
    '''
    Map numpy data types to VIPS data formats.

    Parameters
    ----------
    np_dtype: numpy.dtype

    Returns
    -------
    gi.overrides.Vips.BandFormat
    '''
    lookup = {
        np.dtype('int8'): Vips.BandFormat.CHAR,
        np.dtype('uint8'): Vips.BandFormat.UCHAR,
        np.dtype('int16'): Vips.BandFormat.SHORT,
        np.dtype('uint16'): Vips.BandFormat.USHORT,
        np.dtype('int32'): Vips.BandFormat.INT,
        np.dtype('float32'): Vips.BandFormat.FLOAT,
        np.dtype('float64'): Vips.BandFormat.DOUBLE
    }
    return lookup[np_dtype]


def vips_format_to_np_dtype(vips_format):
    '''
    Map VIPS data formats to numpy data types.

    Parameters
    ----------
    format: gi.overrides.Vips.BandFormat

    Returns
    -------
    numpy.dtype
    '''
    lookup = {
        Vips.BandFormat.CHAR: np.dtype('int8'),
        Vips.BandFormat.UCHAR: np.dtype('uint8'),
        Vips.BandFormat.SHORT: np.dtype('int16'),
        Vips.BandFormat.USHORT: np.dtype('uint16'),
        Vips.BandFormat.INT: np.dtype('int32'),
        Vips.BandFormat.FLOAT: np.dtype('float32'),
        Vips.BandFormat.DOUBLE: np.dtype('float64')
    }
    return lookup[vips_format]


def np_array_to_vips_image(nparray):
    '''
    Convert a `numpy` array to a `Vips` image object.

    Parameters
    ----------
    nparray: numpy.ndarray

    Returns
    -------
    gi.overrides.Vips.image
    '''
    vips_format = np_dtype_to_vips_format(nparray.dtype)
    dims = nparray.shape
    height = dims[0]
    width = 1
    bands = 1
    if len(dims) > 1:
        width = dims[1]
    if len(dims) > 2:
        bands = dims[2]
    img = Vips.Image.new_from_memory_copy(
            nparray.data, width, height, bands, vips_format)

    return img


def vips_image_to_np_array(vips_image):
    '''
    Convert a `Vips` image object to a `numpy` array.

    Parameters
    ----------
    vips_image: gi.overrides.Vips.image

    Returns
    -------
    numpy.ndarray
    '''
    nptype = vips_format_to_np_dtype(vips_image.get_format())
    mem_string = vips_image.write_to_memory()
    if vips_image.bands > 1:
        array = np.fromstring(mem_string, dtype=nptype).reshape(
                    vips_image.height, vips_image.width, vips_image.bands)
    else:
        array = np.fromstring(mem_string, dtype=nptype).reshape(
                    vips_image.height, vips_image.width)
    return array


def create_spacer_image(height, width, dtype, bands):
    '''
    Create a black image that can be inserted as a spacer between
    channel images.

    Parameters
    ----------
    height: int
        dimension of the image in y dimension
    width: int
        dimension of the image in x dimension
    dtype: gi.overrides.Vips.BandFormat
        data type (format) of the image
    bands: int
        number of color dimensions (``1`` for grayscale and ``3`` for RGB)

    Returns
    -------
    gi.overrides.Vips.Image
        black image of specified `dtype`

    '''
    spacer = Vips.Image.black(width, height, bands=bands).cast(dtype)
    return spacer


def hist_sample_from_sites(filenames, nr_to_sample=5):
    '''
    Compute histogram for a set of sampled images.

    Parameters
    ----------
    filenames: List[str]
        names of image files
    nr_to_sample: int, optional
        number of images to sample (defaults to 5)

    Returns
    -------
    numpy.ndarray
        values of the histogram averaged over the sampled images
    '''
    files = rand.sample(filenames, nr_to_sample)
    hist = np.zeros((256,), dtype='uint32')
    for f in files:
        mat = imread(f)
        scaled = bytescale(mat)
        h = np.histogram(scaled, 256)[0]
        hist += h
    hist /= len(files)
    return hist


def find_border_objects(im):
    '''
    Given a label image, find the objects at the border of the image.

    Parameters
    ----------
    im: numpy.ndarray
        label image

    Returns
    -------
    List[int]
        1 if an object represent a border object and 0 otherwise
    '''
    edges = [np.unique(im[0, :]),   # first row
             np.unique(im[-1, :]),  # last row
             np.unique(im[:, 0]),   # first col
             np.unique(im[:, -1])]  # last col

    # Count only unique ids and remove 0 since it signals 'empty space'
    border_ids = list(reduce(set.union, map(set, edges)).difference({0}))
    object_ids = np.unique(im[im != 0])
    return [1 if o in border_ids else 0 for o in object_ids]


def save_hist_to_txt_file(hist, filename):
    np.savetxt(filename, hist, fmt='%d')


def calc_threshold_level(sample_images, percent=99.9):
    '''
    Calculate threshold level for a particular quantile across a set of
    sample images.

    A top threshold percentage of 99.9 would mean that 0.1% of the
    pixels with the largest value should be set to their lowest value.

    The quantile above `threshold_top_percent` pixels is computed for each
    image in `sample_images` and then averaged.

    Parameters
    ----------
    sample_images: List[gi.overrides.Vips.Image[gi.overrides.Vips.BandFormat.USHORT]]
        images that are representative of the images that are to be thresholded
    percent: float, optional
        quantile (default: `99.9`)

    Returns
    -------
    int
        threshold level
    '''

    # `percent` % of all pixels lie below `thresh`
    thresholds = map(lambda img: img.percent(percent), sample_images)
    avg_thresh = int(float(sum(thresholds)) / len(thresholds))
    return avg_thresh


def create_thresholding_LUT(threshold):
    '''
    Construct a 16 bit color lookup table that can be used to threshold images.

    The computed lookup table will set any values above a threshold level
    to that threshold level.

    Parameters
    ----------
    threshold: int
        threshold level

    Returns
    -------
    gi.overrides.Vips.Image
        LUT (= 1 x 2^16 pixel `Vips` image)

    Examples
    --------
    The LUT can be used like this::

        lut = create_thresholding_LUT(some_images, 0.1)
        thresholded_img = img.maplut(lut)  # apply to some image
    '''
    # Create a 1 by 2**16 image (the lookup table) with linear values
    # [0, 1, 2, ..., 2^16-1] that is used to map colors in the original image
    # to new ones. So if a the original gray value for some pixel was 20,
    # then the new pixel value would correspond to the value at position 20
    # in the LUT.
    identity_image = Vips.Image.identity(ushort=True)

    # Transform the LUT in such a way that pixels with values above the
    # threshold get the same value (= threshold).
    condition_image = (identity_image >= threshold)
    return condition_image.ifthenelse(threshold, identity_image)


def convert_to_uint8(img, min_value=None, max_value=None):
    '''
    Convert a 16-bit image to 8-bit by linearly scaling from a given range
    to 0-255. The lower and upper values of the range can be set. If not set
    they default to the minimum and maximum intensity value of `img`.
    
    This can be useful for the display of an image in a figure.

    Parameters
    ----------
    img: numpy.ndarray[uint16]
        image that should be rescaled
    min_value: int, optional
        lower intensity value of rescaling range (default: `None`)
    max_value: int, optional
        upper intensity value of rescaling range (default: `None`)

    Returns
    -------
    numpy.ndarray[uint8]

    Note
    ----
    When no `min_value` or `max_value` is provided the result is equivalent to
    the corresponding method in ImageJ: Image > Type > 8-bit.
    '''
    if min_value is not None:
        if not isinstance(min_value, int):
            raise TypeError('Argument "min_value" must have type int.')
        min_value = min_value
    else:
        min_value = np.min(img)
    if max_value is not None:
        if not isinstance(max_value, int):
            raise TypeError('Argument "max_value" must have type int.')
        max_value = max_value
    else:
        max_value = np.max(img)
    in_range = (min_value, max_value)
    img_rescaled = rescale_intensity(
                    img, out_range='uint8', in_range=in_range).astype(np.uint8)
    return img_rescaled
