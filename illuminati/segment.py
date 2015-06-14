#!/usr/bin/env python
# encoding: utf-8

"""
TissueMAPS tool for creating a segmentation outlines.

    $ tm_segment.py --help
"""

import operator as op
import numpy as np
import h5py
import os
import yaml
from skimage.measure import find_contours, approximate_polygon
import sys
import scipy
from os.path import basename, exists, realpath, join
import util
import re

from gi.repository import Vips


def remove_border_cells_vips(im, is_source_uint16=True):
    """
    Given a site image, set all pixels with
    ids belonging to border cells to zero.

    :im: a VIPS image that represents the site.
    :is_source_uint16: a boolean flag indicating if the source band format
                       is uin16, otherwise its taken as uint8.
    :returns: a new VIPS image with border cell entries set to 0.

    """
    # Extract the edges on each side of the image
    left = im.extract_area(0, 0, 1, im.height)
    right = im.extract_area(im.width-1, 0, 1, im.height)
    top = im.extract_area(0, 0, im.width, 1)
    bottom = im.extract_area(0, im.height-1, im.width, 1)

    for border in [left, right, top, bottom]:
        # Create a histogram, i.e. a 1 x 2^16
        hist = border.hist_find()
        id_lut = Vips.Image.identity(ushort=is_source_uint16)
        is_nonzero = hist > 0
        lut = Vips.Image.ifthenelse(is_nonzero, 0, id_lut)
        im = im.maplut(lut)

    return im


def local_to_global_ids_vips(im, offset_id):
    """
    Add an offset to site-local cell labels and then encode
    that number as a (R, G, B) triple.
    So if at one pixel there was a value of x this would mean
    that that pixel belongs to the xth cell in the image `im`.
    The function would now add `offset_id` to x and encode the resulting value in terms of RGB s.t.
    R * 256^2 + G * 256 + B == x + offset_id

    :im: a vips image where each pixel indicates to which cell this pixel belongs.
    :offset_id: a integer value to add to all labels.
    :returns: a RGB image with band format UCHAR.

    """
    # Convert the image to integer and add an offset to all ids.
    nonzero = im > 0
    im = im.cast('uint')
    im = nonzero.ifthenelse(im + offset_id, 0)
    max_val = int(im.max())

    # Divide the ids in `im` into their R-G-B representation.
    red = (im / 256**2)
    r_rem = (im % 256**2)
    green = (r_rem / 256)
    g_rem = (r_rem % 256)
    blue = g_rem
    rgb = red.bandjoin(green).bandjoin(blue).cast('uchar')
    return rgb, max_val


def remove_border_cells(site_matrix):
    """
    Given a matrix of a site image, set all pixels with
    ids belonging to border cells to zero.

    :site_matrix: a numpy array of the image matrix.
    :returns: a new numpy array with border cell entries set to 0.

    """
    edges = [np.unique(site_matrix[0, :]),   # first row
             np.unique(site_matrix[-1, :]),  # last row
             np.unique(site_matrix[:, 0]),   # first col
             np.unique(site_matrix[:, -1])]  # last col

    # Count only unique ids and remove 0 since it signals 'empty space'
    bordercell_ids = list(reduce(set.union, map(set, edges)).difference({0}))
    mat = site_matrix.copy()  # Copy since we don't update in place
    is_border_cell = np.in1d(mat, bordercell_ids).reshape(mat.shape)
    mat[is_border_cell] = 0
    return mat


def create_id_lookup_matrices(sitemat, offset):
    nonzero = sitemat != 0
    mat = sitemat.astype('uint32')
    mat[nonzero] = mat[nonzero] + offset
    return mat, np.max(mat)


def compute_cell_centroids(sitemat, site_row_nr, site_col_nr, offset):
    """Return a dictionary from cell ids to centroids.
    Centroids are given as (x, y) tuples where the origin of the coordinate
    system is assumed to be in the topleft corner (like in openlayers).

    :sitemat: A numpy matrix containing the cell labels.
    :site_row_nr: The row number of the site.
    :site_col_nr: The col number of the site.
    :site_width: The width of each site as an int.
    :site_height: The height of each site as an int.
    :offset: An integer that is added to all ids in sitemat.
             This should correspond to the maximum id in the previously
             processed site.
    :returns: A (ncells x 3) numpy array of type double.
              Cell ids are located in the first column,
              the x coordinates of the centroids in the second column.
              The y coordinates in the last one.

    """
    height, width = sitemat.shape
    local_ids = np.array(
        sorted(set(np.unique(sitemat)).difference({0})),
        dtype='int32'
    )
    global_ids = local_ids + offset
    ncells = len(local_ids)

    centroids = np.empty((ncells, 3), np.double)
    centroids[:, 0] = global_ids

    for idx, id in enumerate(local_ids):
        i, j = (sitemat == id).nonzero()
        ycoords = i + sitemat.shape[0] * site_row_nr
        xcoords = j + sitemat.shape[1] * site_col_nr
        xmean = np.mean(xcoords)
        ymean = -1 * np.mean(ycoords)
        centroids[idx, 1] = xmean
        centroids[idx, 2] = ymean

    return centroids, np.max(global_ids)


def compute_outline_polygons(site_matrix, contour_level=0.5, poly_tol=0.95):
    """
    Given a matrix of a site image with border cells removed,
    get a list of lists, each consisting of local
    i-j coordinates that make up a polygon.
    :site_matrix: a numpy array of the image matrix where each pixel holds
                  the cell id to which it belongs. Background should be 0.
    :returns: a hash that maps each cell id to a list of polygon vertices
              (local i-j coordinates).
    """
    outlines = {}
    cell_ids = set(np.unique(site_matrix)).difference({0})
    print '* Computing outlines ....'
    for i, cell_id in enumerate(cell_ids):
        print '|_ cell {:0>5} / {}'.format(i + 1, len(cell_ids))

        # Create a bounding box around the cell id of interest
        # The bounding box should have a frame of thickness 1 matrix cell
        i, j = (site_matrix == cell_id).nonzero()
        mini = np.min(i) - 1
        maxi = np.max(i) + 2
        minj = np.min(j) - 1
        maxj = np.max(j) + 2

        nrow, ncol = site_matrix.shape

        if mini < 0 or mini > nrow + 1 or minj < 0 or minj > ncol + 1:
            # If this is the case, this is a border cell and should
            # not be considered
            continue

        submat = site_matrix[mini:maxi, minj:maxj].copy()
        submat[submat != cell_id] = 0

        # find_contours needs arrays that are at least 2x2 big, skip otherwise
        nrow, ncol = submat.shape
        if nrow < 2 or ncol < 2:
            continue

        contours = find_contours(submat, contour_level)
        # Skip if no contours found
        if not contours:
            continue

        if len(contours) != 1:
            # Not really a big problem since in almost all cases
            # the true (largest) contour is the first one
            print '  warning: %d contours found for cell with id %d' \
                % (len(contours), cell_id)

        contour = contours[0]

        poly = approximate_polygon(contour, poly_tol).astype(np.int32)
        if poly is None:
            print '  warning: polygon was None for cell with id  %d' % cell_id
            continue

        # Add the offset of this subimage to all coordinates
        poly += (mini, minj)
        outlines[cell_id] = poly
    return outlines


def save_outline_polygons(outlines, filename):
    try:
        f = h5py.File(filename, 'w')
        for global_cell_id, poly in outlines.items():
            f[global_cell_id] = poly
    finally:
        f.close()


def outlines_vips(im):
    """
    Given a label matrix, return a matrix of the outlines of the labeled objects.

    If a pixel is not zero and has at least one neighbor with a different
    value, then it is part of the outline.

    For more info about how this works, see here:
    http://www.vips.ecs.soton.ac.uk/supported/current/doc/html/libvips/libvips-morphology.html

    """
    # Since the images are sometimes not square, they can't be rotated at all times.
    # Normally you would define one mask and apply it repeatedly to the image while rotating it.
    # Since this isn't possible, I just define all the masks right here.
    # 0 means: 'match a background pixel'
    # 255 means: 'match an object pixel (nonzero pixel)
    # 128 means: 'match any pixel'
    # Note that VIPS uses 255 for TRUE and 0 for FALSE.

    masks = [
        [[0   , 128 , 128]  ,
         [128 , 255 , 128]  ,
         [128 , 255 , 128]] ,
        [[128 , 0   , 128]  ,
         [128 , 255 , 128]  ,
         [128 , 255 , 128]] ,
        [[128 , 128 , 0]    ,
         [0   , 255 , 128]  ,
         [128 , 255 , 128]] ,
        [[0   , 128 , 128]  ,
         [128 , 255 , 255]  ,
         [128 , 128 , 128]] ,
        [[128 , 128 , 128]  ,
         [0   , 255 , 255]  ,
         [128 , 128 , 128]] ,
        [[128 , 128 , 128]  ,
         [128 , 255 , 255]  ,
         [0   , 128 , 128]] ,
        [[128 , 255 , 128]  ,
         [128 , 255 , 128]  ,
         [0   , 128 , 128]] ,
        [[128 , 255 , 128]  ,
         [128 , 255 , 128]  ,
         [128 , 0   , 128]] ,
        [[128 , 255 , 128]  ,
         [128 , 255 , 128]  ,
         [128 , 128 , 0]]   ,
        [[128 , 128 , 128]  ,
         [255 , 255 , 128]  ,
         [128 , 128 , 0]]   ,
        [[128 , 128 , 128]  ,
         [255 , 255 , 0]    ,
         [128 , 128 , 128]] ,
        [[128 , 128 , 0]    ,
         [255 , 255 , 128]  ,
         [128 , 128 , 128]]
    ]

    results = []
    nonbg = im > 0
    # Apply all the masks and save each result
    for i, mask in enumerate(masks):
       img = nonbg.morph(mask, 'erode')
       results.append(img)

    # OR all the images
    images_disj = reduce(op.or_, results)
    return images_disj


def outlines(labels, keep_ids=False):
    """
    Given a label matrix, return a matrix of the outlines of the labeled objects.
    If `keep_ids` is True, the outlines will still consist of their cell's id, otherwise
    all outlines will be 255.
    Note that in the case of keeping the ids, the output matrix will have the original bit depth!

    If a pixel is not zero and has at least one neighbor with a different
    value, then it is part of the outline.

    Taken from the BSD-licensed file:
    https://github.com/CellProfiler/CellProfiler/blob/master/cellprofiler/cpmath/outline.py

    """

    lr_different = labels[1:, :] != labels[:-1, :]
    ud_different = labels[:, 1:] != labels[:, :-1]
    d1_different = labels[1:, 1:] != labels[:-1, :-1]
    d2_different = labels[1:, :-1] != labels[:-1, 1:]
    different = np.zeros(labels.shape, bool)
    different[1:, :][lr_different]  = True
    different[:-1, :][lr_different] = True
    different[:, 1:][ud_different]  = True
    different[:, :-1][ud_different] = True
    different[1:, 1:][d1_different] = True
    different[:-1, :-1][d1_different] = True
    different[1:, :-1][d2_different] = True
    different[:-1, 1:][d2_different] = True

    different[0, :] = False
    different[:, 0] = False
    different[-1, :] = False
    different[:, -1] = False

    if keep_ids:
        return different * labels
    else:
        output = np.zeros(labels.shape, np.uint8)
        output[different] = 255

        return output


def gather_siteinfo(file_grid):

    height = len(file_grid)
    width = len(file_grid[0])
    nsites = height * width
    infomat = np.zeros((nsites, 4), dtype='uint32')

    max_id_up_to_now = 0
    idx = 0
    for i in range(height):
        print 'row: %d' % i
        for j in range(width):
            print 'col: %d' % j
            filename = file_grid[i][j]

            site_re = '_s(\d+)_'
            sitenr = int(re.search(site_re, filename).group(1))
            (rownr, colnr) = map(int, re.search('_r(\d+)_c(\d+)_', filename).groups())
            infomat[idx, :] = (sitenr, rownr, colnr, max_id_up_to_now)

            max_local_id = np.max(scipy.misc.imread(filename))
            max_id_up_to_now += max_local_id

            idx += 1

    return infomat


if __name__ == '__main__':
    import argparse

    desc = """

Create outlines from label matrices which can then be used as overlays in in TissueMAPS.
These outline images need to be stitched together using tm_stitch.py

"""

    parser = argparse.ArgumentParser(description=desc)
    parser.add_argument('files', nargs='*',
                        help='the segmentation image files')

    parser.add_argument('-o', dest='output_dir', required=True,
                        help='where to put the outline images')

    parser.add_argument('-c', '--config', dest='config',
                        default=os.path.join(os.path.dirname(__file__), '..',
                                             'image_toolbox.config'),
                        help='use custom yaml configuration file \
                        (defaults to "image_toolbox" config file)')

    args = parser.parse_args()

    if not args.files or not all(map(util.is_image, args.files)):
        parser.print_help()
        sys.exit(1)

    config_filename = args.config
    if not os.path.exists(config_filename):
        print('Error: configuration file %s does not exist!' % config_filename)
        sys.exit(1)
    print '.. Using configuration file %s' % config_filename
    config_settings = yaml.load(open(config_filename).read())
    util.check_config(config_settings)

    site_images = map(util.Image.from_filename(config_settings), args.files)

    for i, site_image in enumerate(site_images):
        print '* (%d / %d) computing outline for: %s' \
            % (i, len(site_images), basename(site_image.filename))
        mat = site_image.image
        mat = remove_border_cells(mat)
        outline_mat = outlines(mat)

        fname = 'outline-' + basename(site_image.filename)
        fpath = realpath(join(args.output_dir, fname))
        if exists(fpath):
            print 'Error: the path %s exists already. Aborting.' % fpath
            sys.exit(1)
        scipy.misc.imsave(fpath, outline_mat)

