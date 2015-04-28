"""
Utility functions for image pre-processing.
"""

import random as rand
from scipy.misc import imread, bytescale
import numpy as np

from gi.repository import Vips


def save_image_to_file(image_obj, out_filepath):
    """Save a VIPS image object to a file."""
    image_obj.write_to_file(out_filepath)


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


def save_hist_to_txt_file(hist, filename):
    np.savetxt(filename, hist, fmt='%d')


def get_threshold(sample_images, threshold_top_percent=0.1):
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
