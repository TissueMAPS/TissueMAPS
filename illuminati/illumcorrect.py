#!/usr/bin/env python
# encoding: utf-8

"""
TissueMAPS tool for correcting images for illumination artifacts.

    $ tm_illumcorrect.py --help
"""

import numpy as np
import scipy.ndimage as ndi
import h5py
from scipy.misc import imread
import png
import yaml
import os
import re
from os.path import join, realpath, basename, splitext, exists, isdir
import sys
from gi.repository import Vips
import util


class Illumcorrect:

    def __init__(self, config_settings, shift=False):
        """
        Configuration settings provided by YAML file.
        """
        self.cfg = config_settings
        self.shift = shift

    def get_stats_file_name(self, image_filenames):
        """
        Dynamically determine name and location of illumination correction
        statistics file from image filename.
        Variables can be set in the configuration file!
        """
        image_file = image_filenames[0]
        project = util.Project(self.cfg)
        project_dir = project.get_rootdir_from_image_file(image_file)
        channel_nr = project.get_channel_nr_from_filename(image_file)
        stats_file = self.cfg['STATS_FILE_FORMAT'].format(channel_number=channel_nr)

        if self.shift:
            cycles = util.Cycles(self.cfg)
            cycle_nr = cycles.get_cycle_nr_from_filename(image_file)
            cycle_dirs = cycles.get_cycle_directories(project_dir)
            cycle_index = [i for i, x in enumerate(cycle_dirs)
                            if re.search('%d$' % cycle_nr, x.filename)]
            if not len(cycle_index) == 1:
                raise Exception('Cycle subdirectory could not be determined')
            cycle_index = cycle_index[0]
            cycle_subdir = cycle_dirs[cycle_index].filename

            stats_folder = \
                self.cfg['STATS_FOLDER_LOCATION'].format(cycle_subdirectory=cycle_subdir)
        else:
            stats_folder = self.cfg['STATS_FOLDER_LOCATION']

        stats_path = os.path.join(project_dir, stats_folder, stats_file)
        if not os.path.exists(stats_path):
            raise Exception('Illumination correction statistics \
                            filename could not be determined')

        return stats_path


# TODO: The statistics files could also be loaded directly into VIPS
# without having to convert them from an numpy array.
def load_statistics_from_mat_file_vips(stats_path):
    """Load the precomputed statistics into VIPS images"""
    mean_mat, std_mat = load_statistics_from_mat_file(stats_path)
    return map(np_array_to_vips_image, (mean_mat, std_mat))


def load_image_from_file(image_path, dtype='float64'):
    """Load an image file into a np array and return it."""
    return np.array(imread(image_path), dtype=dtype)


def load_image_from_file_vips(image_path):
    """Load an image file into a VIPS image"""
    return Vips.Image.new_from_file(image_path)


def load_statistics_from_mat_file(stats_path):
    """
    Load precomputed statistics for each pixel over all sites, that
    are used to perform the illumination correction.
    By default these mat files are located somewhere like
    'Cycle1/BATCH/Measurements_batch_illcor_channel001_zstack000.mat'.

    :stats_path: path to stats .mat file : string.
    :returns: a tuple of the form (mean_matrix, std_matrix).

    """
    stats = h5py.File(stats_path, 'r')
    stats = stats['stat_values']
    mean_image = np.array(stats['mean'][()], dtype='float64').conj().T
    std_image = np.array(stats['std'][()], dtype='float64').conj().T
    return (mean_image, std_image)


def illum_correction_vips(orig_image, mean_image, std_image):
    """
    Correct fluorescence microscopy image for illumination artifacts using VIPS.

    :orig_image: The VIPS image to be processed.
    :mean_image: The means as a VIPS image
    :std_image: The standard deviations as a VIPS image
    :returns: The corrected image.

    """
    # If we don't cast the conditional image, the result of ifthenelse
    # will be UCHAR
    orig_format = orig_image.get_format()
    cond = (orig_image == 0).cast(orig_format)
    img = cond.ifthenelse(1, orig_image)

    # Do all computations with double precision
    img = img.cast('double')
    img = img.log10()
    img = (img - mean_image) / std_image
    img = img * std_image.avg() + mean_image.avg()  # TODO: Precompute means
    img = 10 ** img

    # Cast back to UINT16 or whatever the original image was
    img = img.cast(orig_format)

    return img


def illum_correction(orig_image, mean_mat, std_mat):
    """
    Correct fluorescence microscopy image_filenames for illumination artifacts.

    :orig_image: original image as a float64 2d numpy array.
    :mean_mat: 2d numpy array with M_ij == mean over all values at position ij.
    :std_mat: 2d numpy with M_ij == stdev over all values at position ij.
    :returns: corrected image : float64 numpy array.

    """
    ### correct intensity image for illumination artifact
    corr_image = orig_image.copy()
    corr_image[corr_image == 0] = 1
    corr_image = (np.log10(corr_image) - mean_mat) / std_mat
    corr_image = (corr_image * np.mean(std_mat)) + np.mean(mean_mat)
    corr_image = 10 ** corr_image

    ### fix "bad" pixels with non numeric values (NaN or Inf)
    ix_bad = np.logical_not(np.isfinite(corr_image))
    if ix_bad.sum() > 0:
        print('   IllumCorr: identified %d bad pixels' % ix_bad.sum())
        med_filt_image = ndi.filters.median_filter(corr_image, 3)
        corr_image[ix_bad] = med_filt_image[ix_bad]
        corr_image[ix_bad] = med_filt_image[ix_bad]

    ### fix extreme pixels
    percent = 99.9999
    thresh = np.percentile(corr_image, percent)
    print('   IllumCorr: %d extreme pixel values (above %f percentile) '
          ' were set to %d' % (np.sum(corr_image > thresh), percent, thresh))
    corr_image[corr_image > thresh] = thresh

    return corr_image.astype(np.uint16)


def save_image(image_mat, out_path, bitdepth=16):
    """Save the numpy matrix `image_mat` to a file with path `out_path`."""
    # img = Image.fromarray(image_mat)
    with open(out_path, 'wb') as f:
        height, width = image_mat.shape
        w = png.Writer(width=width, height=height, bitdepth=bitdepth, greyscale=True)
        w.write(f, image_mat.astype(np.uint16))


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


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(
        description='Applies illumination correction to images')

    # Required args
    parser.add_argument('files', nargs='*',
                        help='image files that should be corrected')
    parser.add_argument('-o', '--output-dir', dest='output_dir', required=True,
                        help='directory where corrected images should be saved')

    parser.add_argument('-c', '--config', dest='config',
                        default=os.path.join(os.path.dirname(__file__), '..',
                                             'config.yaml'),
                        help='use custom yaml configuration file')

    # Optional args
    parser.add_argument('--overwrite', default=False, action='store_true',
                        help='overwrite raw image files (usually a bad idea!)')
    parser.add_argument('--suffix', dest='suffix', default='-corr',
                        help='suffix to append')
    parser.add_argument('--no-vips', dest='no_vips', action='store_true', default=False,
                        help='use numpy instead of vips')

    args = parser.parse_args()

    if not args.files \
       or not args.output_dir \
       or not all(map(util.is_image, args.files)):
        parser.print_help()
        sys.exit(1)

    if not isdir(args.output_dir):
        print 'Error: the directory %s does not exist!' % args.output_dir
        sys.exit(1)

    config_filename = args.config
    if not os.path.exists(config_filename):
        print('Error: configuration file %s does not exist!' % config_filename)
        sys.exit(1)
    print '.. Using configuration file %s' % config_filename
    config_settings = yaml.load(open(config_filename).read())
    util.check_config(config_settings)

    tm_obj = Illumcorrect(config_settings)
    stats_file = tm_obj.get_stats_file_name(args.files)

    if args.no_vips:
        mean, std = load_statistics_from_mat_file(stats_file)
    else:
        mean, std = load_statistics_from_mat_file_vips(stats_file)

    print '* ILLUMINATION CORRECTION'
    for f in args.files:
        print '|_ current file: ' + f

        if args.no_vips:
            img = load_image_from_file(f, dtype='float64')
            corrected_img = illum_correction(img, mean, std)
        else:
            img = load_image_from_file_vips(f)
            corrected_img = illum_correction_vips(img, mean, std)

        # Create the filename, e.g. 'path/to/output_dir/original_filename_suffix.png'
        filepath, ext = splitext(f)
        corrected_img_filename = basename(filepath) + args.suffix + ext
        corrected_img_filepath = \
            realpath(join(args.output_dir, corrected_img_filename))

        file_exists = exists(corrected_img_filepath)
        if not file_exists or file_exists and args.overwrite:
            if args.no_vips:
                save_image(corrected_img, corrected_img_filepath)
            else:
                corrected_img.write_to_file(corrected_img_filepath)
        else:
            basename, ext = os.path.splitext(f)
            corrected_img_filepath = basename + args.suffix + ext

        if not args.vips:
            save_image(corrected_img, corrected_img_filepath)
        else:
            corrected_img.write_to_file(corrected_img_filepath)
            print 'Error: the file %s exists already and overwrite' \
                  ' flag wasn\'t set => abort.' % corrected_img_filepath
            sys.exit(1)

