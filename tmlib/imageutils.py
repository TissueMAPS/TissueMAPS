import random as rand
from scipy.misc import imread, bytescale
import numpy as np
import png
try:
    from gi.repository import Vips
except ImportError as error:
    print 'Vips could not be imported.\nReason: %s' % str(error)


'''Utility functions for common image processing routines.'''


def save_vips_image_jpg(im, filename, quality=75):
    '''
    Save a `Vips` image object to a file as JPEG image.

    Parameters
    ----------
    im: Vips.Image
        image
    filename: str
        name of the output file
    quality: int, optional
        quality of the JPEG image (defaults to 75)
    '''
    im.write_to_file(filename, Q=quality, optimize_coding=True)


def save_image_png_vips(im, filename, bitdepth=16):
    '''
    Save the `Vips` image object to file as PNG image.

    Parameters
    ----------
    im: Vips.Image
        image
    filename: str
        name of the output file
    bitdepth: int, optional
        bit depth of the PNG image (defaults to 16)
    '''
    im.cast('ushort').write_to_file(filename)


def save_image_png_numpy(im, filename, bitdepth=16):
    '''
    Save the `numpy` array to file as PNG image.

    Parameters
    ----------
    im: numpy.ndarray
        image
    filename: str
        name of the output file
    bitdepth: int, optional
        bit depth of the PNG image (defaults to 16)
    '''
    # img = Image.fromarray(image)
    with open(filename, 'wb') as f:
        height, width = im.shape
        w = png.Writer(width=width, height=height,
                       bitdepth=bitdepth, greyscale=True)
        w.write(f, im.astype(np.uint16))


def save_image_png(im, filename):
    '''
    Save image to file in 16-bit PNG format.

    Parameters
    ----------
    im: numpy.ndarray or Vips.Image
        image that should be saved
    filename: str
        path to the image file
    '''
    if isinstance(im, np.ndarray):
        save_image_png_numpy(im, filename)
    else:
        save_image_png_vips(im, filename)


def np_dtype_to_vips_format(np_dtype):
    '''
    Map numpy data types to VIPS data formats.

    Parameters
    ----------
    np_dtype: numpy.dtype

    Returns
    -------
    Vips.BandFormat
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
    format: Vips.BandFormat

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
    Vips.image
    '''
    # Look up what VIPS format corresponds to the type of this np array
    vips_format = np_dtype_to_vips_format(nparray.dtype)

    # VIPS reads the buffer as if the data is saved column by column (column major)
    # but numpy saves it in row major order.
    nparray_trans = nparray.T
    buf = np.getbuffer(nparray_trans)
    height, width = nparray_trans.shape
    img = Vips.Image.new_from_memory(buf, width, height, 1, vips_format)

    # Resulting image has the wrong orientation
    #
    #      |  rotate 90 CW and flip
    #     _|       ------>           ___|
    #
    # (same as horizontal flip and 90 deg CCW, but VIPS can't seem to do CCW rotations)
    img = img.rot(1)
    img = img.flip('horizontal')

    return img.copy()


def vips_image_to_np_array(vips_image):
    '''
    Convert a `Vips` image object to a `numpy` array.

    Parameters
    ----------
    vips_image: Vips.image

    Returns
    -------
    Vips.image
    '''
    nptype = vips_format_to_np_dtype(vips_image.get_format())
    mem_string = vips_image.write_to_memory()
    if vips_image.bands > 1:
        array = np.fromstring(mem_string, dtype=nptype).reshape(
                    vips_image.width, vips_image.height, vips_image.bands)
    else:
        array = np.fromstring(mem_string, dtype=nptype).reshape(
                    vips_image.width, vips_image.height)
    # TODO: 3D RGB images
    return array


def create_spacer_image(dimensions, dtype, bands, direction=None):
    '''
    Create a black image that can be inserted as a spacer between
    channel images.

    Parameters
    ----------
    dimensions: Tuple[int]
        y, x dimensions of the image
    dtype: Vips.BandFormat
        data type (format) of the image
    bands: int
        number of color dimensions (``1`` for grayscale and ``3`` for RGB)
    direction: str, optional
        either ``"horizontal"`` or ``"vertical"``

    Returns
    -------
    Vips.Image
        black spacer image of specified `dtype`, where one dimension is reduced
        to 1% of `dimensions`, depending on the specified `direction`

    Raises
    ------
    ValueError
        when `direction` is not specified correctly
    '''
    if not direction:
        spacer = Vips.Image.black(dimensions[0], dimensions[1],
                                  bands=bands).cast(dtype)
    else:
        if direction == 'vertical':
            spacer = Vips.Image.black(int(dimensions[0]/100), dimensions[1],
                                      bands=bands).cast(dtype)
        elif direction == 'horizontal':
            spacer = Vips.Image.black(dimensions[0], int(dimensions[1]/100),
                                      bands=bands).cast(dtype)
        else:
            raise ValueError('Direction must be "horizontal" or "vertical"')
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
    Given a matrix of a site image, find the objects the border of the image.

    Parameters
    ----------
    im: numpy.ndarray
        label image

    Returns
    -------
    List[int]
        1 if object represent a border object and 0 otherwise

    '''
    edges = [np.unique(im[0, :]),   # first row
             np.unique(im[-1, :]),  # last row
             np.unique(im[:, 0]),   # first col
             np.unique(im[:, -1])]  # last col

    # Count only unique ids and remove 0 since it signals 'empty space'
    border_ids = list(reduce(set.union, map(set, edges)).difference({0}))
    object_ids = np.unique(im[im != 0])
    is_border_object = [1 if o in border_ids else 0 for o in object_ids]
    return is_border_object


def save_hist_to_txt_file(hist, filename):
    np.savetxt(filename, hist, fmt='%d')


def calc_threshold_level(sample_images, threshold_top_percent=0.1):
    '''
    Calculate threshold level for a particular quantile across a set of
    sample images.

    A top threshold percentage of 0.1 would mean that 0.1% of the
    pixels with the largest value should be set to their lowest value.

    The quantile above `threshold_top_percent` pixels is computed for each
    image in `sample_images` and then averaged.

    Parameters
    ----------
    sample_images: List[Vips.Image[Vips.BandFormat.USHORT]]
        images that are representative of the images that are to be thresholded

    threshold_top_percent: float, optional
        quantile (defaults to 0.1)

    Returns
    -------
    int
        threshold level
    '''

    # `percent` % of all pixels lie below `thresh`
    # i.e. `1 - percent` % lie above it.
    percent = 100 - threshold_top_percent
    thresholds = map(lambda img: img.percent(percent), sample_images)
    avg_thresh = int(float(sum(thresholds)) / len(thresholds))
    print '   ... values above %d will be thresholded' % avg_thresh
    return avg_thresh


def create_thresholding_LUT(avg_thresh):
    '''
    Construct a 16 bit color lookup table that can be used to threshold images.

    The computed lookup table will set any values above a threshold level
    to that threshold level.

    Parameters
    ----------
    sample_images: List[Vips.Image[Vips.BandFormat.USHORT]]
        images that are representative of the images that are to be thresholded

    Returns
    -------
    Vips.Image
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
    id_lut = Vips.Image.identity(ushort=True)

    # Transform the LUT in such a way that pixels with values above the
    # threshold get the same value (= threshold).
    cond_image = (id_lut >= avg_thresh)
    lut = cond_image.ifthenelse(avg_thresh, id_lut)

    return lut
