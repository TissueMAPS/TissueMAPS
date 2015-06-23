"""
Utility functions for image pre-processing.
"""

import random as rand
from scipy.misc import imread, bytescale
import numpy as np
import png
from gi.repository import Vips


def save_vips_image_jpg(image_obj, filename, quality=75):
    '''
    Save a VIPS image object to a file as JPEG image.

    Parameters
    ----------
    image_obj: gi.overrides.Vips.Image
    filename: str
    quality: int
             defaults to 75
    '''
    image_obj.write_to_file(filename, Q=quality, optimize_coding=True)


def save_numpy_image_png(image, filename, bitdepth=16):
    '''
    Save the numpy array to file as PNG image.

    Parameters
    ----------
    image: numpy.ndarray
    filename: str
    bitdepth: int
              defaults to 16
    '''
    # img = Image.fromarray(image)
    with open(filename, 'wb') as f:
        height, width = image.shape
        w = png.Writer(width=width, height=height,
                       bitdepth=bitdepth, greyscale=True)
        w.write(f, image.astype(np.uint16))


def np_array_to_vips_image(nparray):
    """Convert a numpy array to a VIPS image"""
    # Dictionary to map VIPS data formats to numpy data formats
    nptype_to_vips_format = {
        np.dtype('int8'): Vips.BandFormat.CHAR,
        np.dtype('uint8'): Vips.BandFormat.UCHAR,
        np.dtype('int16'): Vips.BandFormat.SHORT,
        np.dtype('uint16'): Vips.BandFormat.USHORT,
        np.dtype('int32'): Vips.BandFormat.INT,
        np.dtype('float32'): Vips.BandFormat.FLOAT,
        np.dtype('float64'): Vips.BandFormat.DOUBLE
    }
    # Look up what VIPS format corresponds to the type of this np array
    vips_format = nptype_to_vips_format[nparray.dtype]

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


def hist_sample_from_sites(filenames, nr_to_sample=5):
    files = rand.sample(filenames, nr_to_sample)
    hist = np.zeros((256,), dtype='uint32')
    for f in files:
        mat = imread(f)
        scaled = bytescale(mat)
        h = np.histogram(scaled, 256)[0]
        hist += h
    hist /= len(files)
    return hist


def find_border_objects(site_matrix):
    """
    Given a matrix of a site image, find the objects the border of the image.

    :site_matrix: numpy array of the image matrix.

    :returns:  numpy array with 1 if objects is a border object and 0 otherwise.

    """
    edges = [np.unique(site_matrix[0, :]),   # first row
             np.unique(site_matrix[-1, :]),  # last row
             np.unique(site_matrix[:, 0]),   # first col
             np.unique(site_matrix[:, -1])]  # last col

    # Count only unique ids and remove 0 since it signals 'empty space'
    border_ids = list(reduce(set.union, map(set, edges)).difference({0}))
    object_ids = np.unique(site_matrix[site_matrix != 0])
    is_border_object = [1 if o in border_ids else 0 for o in object_ids]
    return is_border_object


def save_hist_to_txt_file(hist, filename):
    np.savetxt(filename, hist, fmt='%d')


def calc_threshold_level(sample_images, threshold_top_percent=0.1):
    """
    Construct a 16 bit color lookup table that can be used to threshold images.

    A top threshold percentage of 0.1 would mean that 0.1 % of the
    pixels with the largest value should be set to their lowest value.

    The quantile above with there are `threshold_top_percent` pixels is computed
    for each image in `sample_images` and then averaged.

    :sample_images: a list of USHORT VIPS images that are representative
                    of the images that are to be thresholded.

    :threshold_top_percent:
    """

    # `percent` % of all pixels lie below `thresh`
    # i.e. `1 - percent` % lie above it.
    percent = 100 - threshold_top_percent
    thresholds = map(lambda img: img.percent(percent), sample_images)
    avg_thresh = int(float(sum(thresholds)) / len(thresholds))
    print '   ... values above %d will be thresholded' % avg_thresh
    return avg_thresh


def create_thresholding_LUT(avg_thresh):
    """
    Construct a 16 bit color lookup table that can be used to threshold images.

    The computed lookup table will set any values above a threshold to that threshold.

    The LUT is then used like this:

    lut = create_thresholding_LUT(some_images, 0.1)
    thresholded_img = img.maplut(lut)  # apply to some image

    :sample_images: a list of USHORT VIPS images that are representative
                    of the images that are to be thresholded.
    :returns: a LUT (= 1 x 2^16 pixel VIPS image)

    """

    # Create a 1 by 2**16 image (the lookup table) with linear values
    # [0, 1, 2, ..., 2^16-1] that is used to map colors in the original image to new ones.
    # So if a the original gray value for some pixel was 20, then the new pixel value
    # would correspond to the value at position 20 in the LUT.
    id_lut = Vips.Image.identity(ushort=True)

    # Transform the LUT in such a way that pixels with values above the threshold
    # get the same value (= threshold).
    cond_image = (id_lut >= avg_thresh)
    lut = cond_image.ifthenelse(avg_thresh, id_lut)

    return lut
