#!/usr/bin/env python
# encoding: utf-8
import os
import sys
import copy
import yaml
import numpy as np
from shapely.geometry import box
from shapely.geometry.polygon import Polygon
from gi.repository import Vips
from image_toolbox.image import Image
from image_toolbox.image import is_image_file
from image_toolbox.util import load_config, check_config
import imageutil

"""
TissueMAPS tool for stitching individual images together to one large image.
Images can optionally be shifted if required.

    $ stitch.py --help

"""


def build_file_grid(images):
    """
    Build a 2D list of file names that indicates how images should be stitched.
    The function `get_coord_for_image` is called for each file name and
    its return value indicates the 0-based coordinates
    of where the image file should reside in the resulting stitched image.

    :images: objects of class "Image" : [Image]
    :returns: row and column of the image : (int, int)

    """
    image_indices = [i.indices for i in images]
    height = max([c[0] for c in image_indices]) + 1
    width = max([c[1] for c in image_indices]) + 1
    grid = [[None for j in range(width)] for i in range(height)]
    for img, coord in zip(images, image_indices):
        i, j = coord
        grid[i][j] = img
    return grid


def stitch_all_images(vips_image_grid):
    """
    Stitch all images according to the format given in the 2D-list of
    file paths `file_grid`.
    The VIPS image object that is returned can be saved with
    `save_image_to_file` or processed further.

    :vips_image_grid: a 2D list holding all vips images : list[list[Vips.Image]].
    :returns: the VIPS image object.

    """

    grid_height = len(vips_image_grid)
    row_images = []
    for i in range(grid_height):
        # Stitch them together
        images_in_row = vips_image_grid[i]
        row_image = reduce(lambda x, y: x.join(y, 'horizontal'), images_in_row)
        row_images.append(row_image)

    whole_image = reduce(
        lambda x, y: x.join(y, 'vertical'), row_images)

    return whole_image


def shift_stitched_image(vips_img, cycles, current_cycle):
    """
    Shift the image in such a way that all images overlay each other.

    The shift descriptor files assume an inverted y-axis.
    An x-shift of "+2" means that the image is shifted 2 pixel to the right
    with regards to the reference image (the last cycle).
    An y-shift of "+3" would mean that the image is shifted 3 pixel downwards
    w.r.t. the reference.

    :vips_img: the VIPS image to crop.
    :cycles: cycle objects holding shift information : [Subexperiment].
    :returns: the cropped VIPS image.

    """
    shift_descriptors = [c.project.shift_file for c in cycles]
    cycle_nrs = [c.cycle for c in cycles]
    current_cycle_idx = cycle_nrs.index(current_cycle)

    x_shifts = [np.median(desc['xShift']) for desc in shift_descriptors]
    y_shifts = [np.median(desc['yShift']) for desc in shift_descriptors]

    width, height = vips_img.width, vips_img.height  # size of the image

    # Create a Shapely rectangle for each image
    boxes = [box(x, y, x + width, y + height)
             for x, y in zip(x_shifts, y_shifts)]

    # Compute the intersection of all those rectangles
    this_box = boxes[current_cycle_idx].bounds
    intersection = reduce(Polygon.intersection, boxes)
    minx, miny, maxx, maxy = intersection.bounds

    # How much to cut from the left side and from the top
    offset_left = minx - this_box[0]
    offset_top = miny - this_box[1]

    # How large the area to extract is (= the dimensions of the intersection)
    intersection_width = maxx - minx
    intersection_height = maxy - miny

    cropped_image = vips_img.extract_area(
        offset_left, offset_top, intersection_width, intersection_height)

    return cropped_image


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Stitch images')
    parser.add_argument('files', nargs='*',
                        help='image files to process (pattern),\
                        e.g. TIFF/*.png')

    parser.add_argument('-o', dest="output_dir", default=None,
                        help='directory where stitched image should be saved')

    parser.add_argument('-c', '--config', dest='config',
                        default=os.path.join(os.path.dirname(__file__), '..',
                                             'image_toolbox.config'),
                        help='use custom yaml configuration file \
                        (defaults to "image_toolbox" config file)')

    parser.add_argument('-s', '--shift', dest='shift',
                        action='store_true', default=False,
                        help="shift stitched image according to descriptor file")

    args = parser.parse_args()

    if not args.files or not all(map(is_image_file, args.files)):
        parser.print_help()
        sys.exit(1)

    if not args.output_dir:
        print 'You need to specify an output filename'
        sys.exit(1)

    config_filename = args.config
    if not os.path.exists(config_filename):
        print('Error: configuration file %s does not exist!' % config_filename)
        sys.exit(1)
    print '.. Using configuration file %s' % config_filename
    config_settings = load_config(config_filename)
    check_config(config_settings)

    files = args.files
    images = [Image(f, config_settings, vips=True) for f in files]
    experiment_dir = images[0].experiment_dir
    cycles = Experiment(experiment_dir, config).subexperiments

    file_grid = build_file_grid(images)
    vips_image_grid = copy.deepcopy(file_grid)

    print '* LOADING IMAGES'
    for i in range(len(file_grid)):
        for j in range(len(file_grid[0])):
            vips_image_grid[i][j] = file_grid[i][j].image

    stitched_img = stitch_all_images(vips_image_grid)

    if args.shift:
        print '* SHIFTING IMAGES'
        stitched_img = shift_and_crop_stitched_image(stitched_img, cycles)

    print '* STITCHING IMAGES'
    output_file = os.path.join(args.output_dir, 'stitched.png')
    imageutil.save_image_to_file(stitched_img, output_file)
