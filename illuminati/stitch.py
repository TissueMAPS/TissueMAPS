#!/usr/bin/env python
# encoding: utf-8

"""
TissueMAPS tool for stitching individual images together to one large image.
Images can optionally be shifted if required.

    $ tm_stitch.py --help

"""

import re
import os
import sys
import json
import copy
import yaml
import numpy as np
from os.path import join, isdir
from shapely.geometry import box
from shapely.geometry.polygon import Polygon
from gi.repository import Vips
from illuminati import util
from illuminati import imageutil


class stitch:

    def __init__(self, config_settings):
        """
        Configuration settings provided by YAML file.
        """
        self.cfg = config_settings

    def load_shift_descrs(self, root_dir):
        """
        Load the shift descriptor json files according to the path
        given in the config file.
        """
        # Try to find all cycle subdirectories
        dir_content = os.listdir(root_dir)
        regexp = util.regex_from_format_string(self.cfg['CYCLE_SUBDIRECTORY_NAME_FORMAT'])

        def is_cycle_dir(dirname):
            return re.match(regexp, dirname) and isdir(join(root_dir, dirname))

        cycle_dirs = filter(is_cycle_dir, dir_content)
        shift_desc_location = self.cfg['SHIFT_DESCRIPTOR_FILE_LOCATION']
        descr_files = [shift_desc_location.format(cycle_subdirectory=cycle_dir)
                       for cycle_dir in cycle_dirs]
        descr_files = [join(root_dir, p) for p in descr_files]

        descrs = []
        for path in descr_files:
            with open(path, 'r') as f:
                descrs.append(json.load(f))
        return descrs

    def build_file_grid(self, image_paths):
        """
        Build a 2-d list of file names that indicates how images should be stitched.
        The function `get_coord_for_image` is called for each file name and
        its return value indicates the 0-based coordinates
        of where the image file should reside in the resulting stitched image.

        :image_paths: the image paths : [string]
        :returns: row and column of the image : (int, int)

        """
        pattern = np.repeat(self.cfg['COORDINATE_FROM_FILENAME'],
                            len(image_paths), axis=0)
        one_based = np.repeat(self.cfg['COORDINATES_IN_FILENAME_ONE_BASED'],
                              len(image_paths), axis=0)
        image_coords = map(util.get_coord_by_regex, image_paths,
                           pattern, one_based)
        height = max([c[0] for c in image_coords]) + 1
        width = max([c[1] for c in image_coords]) + 1
        grid = [[None for j in range(width)] for i in range(height)]
        for img, coord in zip(image_paths, image_coords):
            if util.is_image(img):
                i, j = coord
                grid[i][j] = img
            else:
                raise Exception(
                    'Can\'t build file grid for stitching'
                    ' with non-image file: ' + img)
        return grid


def stitch_all_images(vips_image_grid):
    """
    Stitch all images according to the format given in the 2d-list of
    file paths `file_grid`.
    The VIPS image object that is returned can be saved with
    `save_image_to_file` or processed further.

    :vips_image_grid: a 2-d list holding all vips images : list[list[Vips.Image]].
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


def global_shift(vips_img, current_idx, shift_descrs):
    """
    Crop the image in such a way that all images overlay each other.

    The shift descriptor files assume an inverted y-axis.
    An x-shift of "+2" means that the image is shifted 2 pixel to the right
    with regards to the reference image (the last cycle).
    An y-shift of "+3" would mean that the image is shifted 3 pixel downwards
    w.r.t. the reference.

    :vips_img: the VIPS image to crop.
    :current_idx: the index of the current cycle (0-based).
    :shift_descrs: a list of all shift descriptors : list[hash]
    :returns: the cropped VIPS image.

    """
    x_shifts = [np.median(desc['xShift']) for desc in shift_descrs]
    y_shifts = [np.median(desc['yShift']) for desc in shift_descrs]

    width, height = vips_img.width, vips_img.height  # size of the image

    # Create a Shapely rectangle for each image
    boxes = [box(x, y, x + width, y + height)
             for x, y in zip(x_shifts, y_shifts)]

    # Compute the intersection of all those rectangles
    this_box = boxes[current_idx].bounds
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
                        default=os.path.join(os.path.dirname(__file__),
                                             'config.yaml'),
                        help='use custom yaml configuration file')

    parser.add_argument('-s', '--shift', dest='shift',
                        action='store_true', default=False,
                        help="shift stitched image according to descriptor file")

    args = parser.parse_args()

    if not args.files or not all(map(util.is_image, args.files)):
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
    config_settings = yaml.load(open(config_filename).read())
    util.check_config(config_settings)

    files = args.files

    config_obj = stitch(config_settings)
    file_grid = config_obj.build_file_grid(files)
    vips_image_grid = copy.deepcopy(file_grid)

    print '* LOADING IMAGES'
    for i in range(len(file_grid)):
        for j in range(len(file_grid[0])):
            im = Vips.Image.new_from_file(file_grid[i][j])
            vips_image_grid[i][j] = im

    stitched_img = stitch_all_images(vips_image_grid)

    if args.shift:
        print '* SHIFTING IMAGES'
        root_dir = util.get_rootdir_from_image_file(files[0])
        cycle_nr = util.get_cycle_nr_from_filename(files[0])
        cycle_dirs = util.get_cycle_directories(root_dir)
        cycle_nrs = sorted([c.cycle_number for c in cycle_dirs])
        shift_desc_idx = cycle_nrs.index(cycle_nr)
        tm_obj = stitch(config_settings)
        descrs = tm_obj.load_shift_descrs(root_dir)
        stitched_img = global_shift(stitched_img, shift_desc_idx, descrs)

    print '* STITCHING IMAGES'
    output_file = os.path.join(args.output_dir, 'stitched.png')
    imageutil.save_image_to_file(stitched_img, output_file)
