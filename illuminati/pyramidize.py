#!/usr/bin/env python
# encoding: utf-8

import os
from gi.repository import Vips
from illuminati import util

"""
TissueMAPS tool for creating a pyramid of a stitched image.

    $ tm_pyramidize.py --help
"""


# TODO: In the current state these pyramids will be 16 bit, but is this necessary? If we rescale the histogram beforehand, we could easily do with 8 bit.
# Also, zoomifysource.js has to be modified to allow png tiles. Even then, normal monitors (and browsers etc.) probably don't even support 16 bit.
def create_pyramid(vips_img, pyramid_dir_name,
                   tile_file_extension='.jpg[Q=100]'):
    """
    Create pyramid of the VIPS image `vips_img` in directory `pyramid_dir_name`
    """
    # If one wants to create 16 bit pyramids the suffix has to be PNG since otherwise the 16-bit images will be automatically converted to 8-bit JPEGs
    vips_img.dzsave(
        pyramid_dir_name, layout='zoomify', suffix=tile_file_extension)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Create a pyramid image')
    parser.add_argument('file',
                        help='stitched image to use for pyramid creation')
    parser.add_argument('-o', dest="output_dir", default=None,
                        help='directory where pyramid should be saved')
    args = parser.parse_args()
    if not args.file or not util.is_image(args.file):
        parser.print_help()

    pyramid_dir_name = args.output_dir or os.path.splitext(args.file)[0]

    img = Vips.Image.new_from_file(args.file)

    print '* CREATING PYRAMID IN DIRECTORY %s' % pyramid_dir_name
    create_pyramid(img, pyramid_dir_name)
