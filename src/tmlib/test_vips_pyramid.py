#! /usr/bin/env python
import os
import numpy as np
import shutil
import tempfile
import itertools
import logging
import argparse
from gi.repository import Vips


def configure_logging():
    logger = logging.getLogger()

    fmt = '%(asctime)s | %(name)-30s | %(levelname)-8s | %(message)s'
    datefmt = '%Y-%m-%d %H:%M:%S'
    formatter = logging.Formatter(fmt=fmt, datefmt=datefmt)

    handler = logging.StreamHandler()
    handler.name = 'stream'
    handler.setFormatter(formatter)
    logger.addHandler(handler)


if __name__ == '__main__':

    configure_logging()

    parser = argparse.ArgumentParser('Test program for Vips pyramid creation.')
    parser.add_argument(
        '-v', '--verbosity', action='count', default=0,
        help='increase logging verbosity')
    parser.add_argument(
        '-m', '--mosaic_axis_length', default=2, type=int,
        help='number of images along each dimension of a mosaic (default: 2)')
    parser.add_argument(
        '-o', '--overview_axis_length', default=5, type=int,
        help='number of mosaics along each dimension of the overview (default: 5)')

    tmp_dir = tempfile.gettempdir()

    args = parser.parse_args()

    logging_level_mapper = {
        0: logging.CRITICAL,
        1: logging.INFO,
        2: logging.DEBUG,
    }

    logger = logging.getLogger('test_vips_pyramid')
    logger.setLevel(logging_level_mapper[args.verbosity])

    vips_logger = logging.getLogger('gi.overrides.Vips')
    vips_logger.setLevel(logging.CRITICAL)

    # Create a squared "overview" image that is composed of many smaller squared
    # "mosaics", each of which is composed of several individual images.
    # NOTE: The size of the actual overview images is at least 0.5 * 10^6 pixels
    # along each dimension.
    mosaic_axis_length = args.mosaic_axis_length
    files = ['file_%d.png' % i for i in range(mosaic_axis_length**2)]

    overview_axis_length = args.overview_axis_length
    folder_names = ['directory_%d' % i for i in range(overview_axis_length**2)]

    input_dir = os.path.join(tmp_dir, 'vips_test', 'inputs')
    if os.path.exists(input_dir):
        shutil.rmtree(input_dir)
    os.makedirs(input_dir)

    output_dir = os.path.join(tmp_dir, 'vips_test', 'outputs')
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)

    directories = [os.path.join(input_dir, f) for f in folder_names]

    # Create images on disk
    # NOTE: The actual images would already exist on disk
    logger.info('create images')
    for d in directories:
        if not os.path.exists(d):
            os.mkdir(d)
        for f in files:
            filename = os.path.join(input_dir, d, f)
            logger.debug('write image to file: %s', filename)
            img = Vips.Image.gaussnoise(100, 100)
            img.write_to_file(filename)

    logger.info('create mosaics')
    moasic_coordinates = list(itertools.product(
                             range(mosaic_axis_length),
                             range(mosaic_axis_length)))
    mosaics = list()
    for i, d in enumerate(directories):
        logger.debug('stitch mosaic # %d', i)
        # Build grid for the current subpart of the final overview image
        mosaic_grid_dims = (mosaic_axis_length, mosaic_axis_length)
        mosaic_grid = np.empty(mosaic_grid_dims, dtype='O')
        for i, coords in enumerate(moasic_coordinates):
            filename = os.path.join(d, files[i])
            mosaic_grid[coords[0], coords[1]] = filename

        # Load individual images and stitch them together
        for r in xrange(mosaic_grid.shape[0]):
            for c in xrange(mosaic_grid.shape[1]):

                img = Vips.Image.new_from_file(
                            mosaic_grid[r, c],
                            access=Vips.Access.SEQUENTIAL)

                if c == 0:
                    row = img
                else:
                    row = row.join(img, 'horizontal', shim=0)

            if r == 0:
                mosaic = row
            else:
                mosaic = mosaic.join(row, 'vertical', shim=0)

        mosaics.append(mosaic)

    # Stitch mosaics together
    logger.info('create overview')
    overview_coordinates = list(itertools.product(
                              range(overview_axis_length),
                              range(overview_axis_length)))
    # Build grid for the final overview image
    overview_grid_dims = (overview_axis_length, overview_axis_length)
    overiew_grid = np.empty(overview_grid_dims, dtype='O')
    for i, coords in enumerate(overview_coordinates):
        overiew_grid[coords[0], coords[1]] = mosaics[i]

    # Create spacer images, which will be inserted between individual mosaics
    space = 10
    dtype = img.get_format()
    col_spacer = Vips.Image.black(space, mosaic.height, bands=1).cast(dtype)
    row_width = (
        mosaic.width * overview_grid_dims[1] +
        space * (overview_grid_dims[1] + 1)
    )
    row_spacer = Vips.Image.black(row_width, space, bands=1).cast(dtype)

    overview = row_spacer
    for r in xrange(overiew_grid.shape[0]):
        for c in xrange(overiew_grid.shape[1]):

            if c == 0:
                row = col_spacer

            mosaic = overiew_grid[r, c]
            row = row.join(mosaic, 'horizontal', shim=space)

        overview = overview.join(row, 'vertical', shim=space)

    overview.join(row_spacer, 'vertical')

    # Rescale overview image to 8-bit
    logger.info('rescale intensities')
    max_value = 2**12
    overview = (overview.cast('float') / max_value * 255).cast('uchar')

    # Save overview image as pyramid on disk
    logger.info('create pyramid: %s', output_dir)
    overview.dzsave(output_dir, layout='zoomify')
