import re
import operator as op
from gi.repository import Vips
import numpy as np
import h5py
import scipy
import logging
from skimage.measure import find_contours
from skimage.measure import approximate_polygon
from .. import image_utils

logger = logging.getLogger(__name__)


def local_to_global_ids_vips(im, offset_id):
    '''
    Add an offset to site-local cell labels and then encode
    that number as a (R, G, B) triple.
    So if at one pixel there was a value of x this would mean
    that that pixel belongs to the xth cell in the image `im`.
    The function would now add `offset_id` to x and encode the resulting value
    in terms of RGB s.t. R * 256^2 + G * 256 + B == x + offset_id

    Parameters
    ----------
    im: Vips.Image
        each pixel indicates to which object this pixel belongs
    offset_id: int
        value to add to all labels

    Returns
    -------
    Vips.Image
        RGB image with band format UCHAR
    '''
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


def create_id_lookup_matrices(sitemat, offset):
    '''
    Create lookup matrices of global object ids by adding an `offset` to the
    local, site-specific ids.

    Parameters
    ----------
    sitemat: numpy.ndarray
        image matrix where pixel values represent site-specific object ids
    offset: int
        value that will be added to each object id

    Returns
    -------
    Tuple[numpy.ndarray[np.uint32], np.uint32]
    '''
    nonzero = sitemat != 0
    mat = sitemat.astype('uint32')
    mat[nonzero] = mat[nonzero] + offset
    return mat, np.max(mat)


def remove_border_objects_numpy(im):
    '''
    Given a matrix of a site image, set all pixels with
    ids belonging to border objects to zero.

    Parameters
    ----------
    im: numpy.ndarray
        image matrix with values corresponding to object ids

    Returns
    -------
    numpy.ndarray
        modified image matrix with pixel values of border objects set to 0
    '''
    is_border_object = image_utils.find_border_objects(im)
    mat = im.copy()
    mat[is_border_object] = 0
    return mat


def remove_border_objects_vips(im, is_source_uint16=True):
    '''
    Given a matrix of a site image, set all pixels with
    ids belonging to border objects to zero.

    Parameters
    ----------
    im: Vips.Image
        image matrix with values corresponding to object ids
    is_source_uint16: bool, optional
        indicating if the source band format is uin16 (defaults to uint8)

    Returns
    ------- 
    Vips.Image
        modified image matrix with pixel values of border objects set to 0
    '''
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


def remove_objects_numpy(im, ids):
    '''
    Given a matrix of a site image, set all pixels whose values
    are in "ids" to zero.

    Parameters
    ----------
    im: numpy.ndarray
        image matrix with values corresponding to object ids
    ids: List[int]
        unique object ids

    Returns
    -------
    numpy.ndarray
        modified image matrix with pixel values in `ids` set to 0
    '''
    mat = im.copy()  # Copy since we don't update in place
    remove_ix = np.in1d(mat, ids).reshape(mat.shape)
    mat[remove_ix] = 0
    return mat


def remove_objects_vips(im, ids, is_source_uint16=True):
    '''
    Given a matrix of a site image, set all pixels whose values
    are in "ids" to zero.

    Parameters
    ----------
    im: Vips.Image
        image matrix with values corresponding to object ids
    ids: List[int]
        unique object ids
    is_source_uint16: bool, optional
        indicating if the source band format is uin16 (defaults to uint8)

    Returns
    -------
    Vips.Image
        modified image matrix with pixel values in ids set to 0
    '''
    id_lut = Vips.Image.identity(ushort=is_source_uint16)
    for i in ids:
        id_lut = (id_lut == i).ifthenelse(0, id_lut)
    im = im.maplut(id_lut)
    return im


def compute_cell_centroids(sitemat, site_row_nr, site_col_nr, offset):
    '''
    Return a dictionary from cell ids to centroids.
    Centroids are given as (x, y) tuples where the origin of the coordinate
    system is assumed to be in the topleft corner (like in openlayers).

    Parameters
    ----------
    sitemat: numpy.ndarray[int]
        image matrix containing the cell labels
    site_row_nr: int
        row number of the site
    site_col_nr: int
        col number of the site
    site_width: int
        width of each site
    site_height: int
        height of each site
    offset: int
        value that is added to all ids in sitemat
        (maximum id in the previously processed .site_ix)

    Returns
    -------
    Tuple[numpy.ndarray[float], int]
        cell ids are located in the first column, the x coordinates of the
        centroids in the second column, and the y coordinates in the last one
    '''
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


def compute_outline_polygons(im, offset_y=0, offset_x=0,
                             contour_level=0.5, poly_tol=0.95,):
    '''
    Given a matrix of a site image with border cells removed,
    get a list of lists, each consisting of local
    i-j coordinates that make up a polygon.

    Parameters
    ----------
    im: numpy.ndarray
        image matrix where pixel values encode cell ids (background is 0)
    offset_y: int, optional
        offset in y direction, which is added to each polygons y coordinate
    offset_x: int, optional
        offset in x direction, which is added to each polygons x coordinate

    Returns
    -------
    Dict
        a hash that maps each cell id to a list of polygon vertices
        (local i-j coordinates)

    Note
    ----
    Objects at the border of the image are automatically discarded.
    '''
    outlines = {}
    cell_ids = set(np.unique(im)).difference({0})
    for i, cell_id in enumerate(cell_ids):

        # Create a bounding box around the cell id of interest
        # The bounding box should have a frame of thickness 1 matrix cell
        i, j = (im == cell_id).nonzero()
        mini = np.min(i) - 1
        maxi = np.max(i) + 2
        minj = np.min(j) - 1
        maxj = np.max(j) + 2

        nrow, ncol = im.shape

        if mini < 0 or mini > nrow + 1 or minj < 0 or minj > ncol + 1:
            # If this is the case, this is a border cell and should
            # not be considered
            continue

        submat = im[mini:maxi, minj:maxj].copy()
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
            logger.warn('%d contours found for cell with id %d',
                        len(contours), cell_id)

        contour = contours[0]

        poly = approximate_polygon(contour, poly_tol).astype(np.int32)
        if poly is None:
            logger.warn('polygon was None for cell with id  %d', cell_id)
            continue

        # Add the offset of this subimage to all coordinates
        poly += (mini, minj)
        poly += (offset_y, offset_x)
        outlines[cell_id] = poly
    return outlines


def save_outline_polygons(outlines, filename):
    try:
        f = h5py.File(filename, 'w')
        for global_cell_id, poly in outlines.items():
            f[global_cell_id] = poly
    finally:
        f.close()


def compute_outlines_numpy(labels, keep_ids=False):
    '''
    Given a label matrix, return a matrix of the outlines of labeled objects.
    If `keep_ids` is True, the outlines will still consist of their cell's id,
    otherwise the outlines will be ``True`` and all other pixels ``False``.
    Note that in the case of keeping the ids,
    the output matrix will have the original bit depth!

    If a pixel is not zero and has at least one neighbor with a different
    value, then it is part of the outline.

    Taken from the BSD-licensed file:
    https://github.com/CellProfiler/CellProfiler/blob/master/cellprofiler/cpmath/outline.py
    '''
    lr_different = labels[1:, :] != labels[:-1, :]
    ud_different = labels[:, 1:] != labels[:, :-1]
    d1_different = labels[1:, 1:] != labels[:-1, :-1]
    d2_different = labels[1:, :-1] != labels[:-1, 1:]
    different = np.zeros(labels.shape, bool)
    different[1:, :][lr_different] = True
    different[:-1, :][lr_different] = True
    different[:, 1:][ud_different] = True
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
        output = np.zeros(labels.shape, np.bool)
        output[different] = True
        return output


def compute_outlines_vips(im):
    '''
    Given a label matrix, return a matrix of the outlines of labeled objects.

    If a pixel is not zero and has at least one neighbor with a different
    value, then it is part of the outline.

    For more info about how this works, see
    `libvips-morphology <http://www.vips.ecs.soton.ac.uk/supported/current/doc/html/libvips/libvips-morphology.html>`_
    '''
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
    nonbg = im > 0  # how can we preserve ids?
    # Apply all the masks and save each result
    for i, mask in enumerate(masks):
        img = nonbg.morph(mask, 'erode')
        results.append(img)

    # Combine all the images
    images_disj = reduce(op.or_, results)
    return images_disj


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
            (rownr, colnr) = map(int, re.search('_r(\d+)_c(\d+)_',
                                                filename).groups())
            infomat[idx, :] = (sitenr, rownr, colnr, max_id_up_to_now)

            max_local_id = np.max(scipy.misc.imread(filename))
            max_id_up_to_now += max_local_id

            idx += 1

    return infomat
