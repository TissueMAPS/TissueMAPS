# TmLibrary - TissueMAPS library for distibuted image analysis routines.
# Copyright (C) 2016-2018 University of Zurich.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
import logging
import numpy as np
from sklearn.cluster import KMeans
import itertools

from tmlib.errors import MetadataError

logger = logging.getLogger(__name__)


def guess_stitch_dimensions(n_sites, stitch_major_axis='vertical'):
    '''Guesses dimensions of a stitched mosaic image. In case `n_sites` is not
    divisible by two, a larger mosaic will be selected that fits `n_sites`.

    Parameters
    ----------
    n_sites: int
        total number of sites (individual images) in the stitched mosaic image
    stitch_major_axis: str, optional
        ``"horizontal"`` if there are more columns than rows and
        ``"vertical"`` otherwise (default: ``"vertical"``)

    Returns
    -------
    Tuple[int]
        number of rows and columns of the stitched mosaic image

    Raises
    ------
    TypeError
        when value of `n_sites` is not an integer
    ValueError
        when value of `stitch_major_axis` is neither ``"horizontal"`` nor
        ``"vertical"`` or when value of `n_sites` is not a positive integer
    IndexError
        when dimensions cannot be determined
    '''
    if stitch_major_axis == 'vertical':
        decent = True
    elif stitch_major_axis == 'horizontal':
        decent = False
    else:
        raise ValueError(
            'Argument "stitch_major_axis" must be either "vertical" or '
            '"horizontal".'
        )

    if not isinstance(n_sites, int):
        raise TypeError(
            'Argument "n_sites" must have type int.'
        )
    if n_sites < 1:
        raise ValueError(
            'Argument "n_sites" must be a positive integer.'
        )
    elif n_sites < 4:
        n = 2
    else:
        n = int(np.sqrt(n_sites))

    v = np.arange(n - n, n + n + 1)
    m = np.matrix(v).conj().T * np.matrix(v)
    t =  np.triu(m)
    d = t - n_sites
    y, x = np.where(d == np.min(d[d >= 0]))
    if len(y) == 0 and len(x) == 0:
        raise IndexError('Stitch dimensions could not be determined.')
    if np.any(y == x):
        dim = v[y[y == x][0]]
        return (dim, dim)
    else:
        return tuple(sorted([v[y[0]], v[x[0]]], reverse=decent))


def calc_stitch_dimensions(stage_positions):
    '''Determines stitch dimensions from stage positions.

    Parameters
    ----------
    stage_positions: List[Tuple[float]]
        stage positions in row (x) and column (y) direction

    Returns
    -------
    Tuple[int]
        number of rows and columns of the stitched mosaic image
    '''
    row_positions = [p[0] for p in stage_positions]
    col_positions = [p[1] for p in stage_positions]
    n_rows = len(set(row_positions))
    n_cols = len(set(col_positions))
    return (n_rows, n_cols)


def calc_stitch_layout(stitch_dims, stage_positions):
    '''Determines the stitch layout of the mosaic image, i.e. in which order
    individual images need to be stitched together.

    Parameters
    ----------
    stitch_dims: Dict[str, int]
        number of rows and columns of the stitched mosaic image
    stage_positions: Tuple[float]
        stage positions in row (x) and column (y) direction

    Returns
    -------
    str
        stitch layout: "horizontal", "zigzag_horizontal", "vertical", or
        "zigzag_vertical"

    Raises
    ------
    ValueError
        when stitch layout can't be determined
    '''
    n_rows = stitch_dims[0]
    n_cols = stitch_dims[1]

    row_positions = [p[0] for p in stage_positions]
    col_positions = [p[1] for p in stage_positions]

    row_1_constant = row_positions[0] == row_positions[n_cols-1]
    row_1_increasing = row_positions[0] < row_positions[n_cols-1]
    row_2_increasing = row_positions[n_cols] < row_positions[(2*n_cols)-1]

    col_1_constant = col_positions[0] == col_positions[n_rows-1]
    col_1_increasing = col_positions[0] < col_positions[n_rows-1]
    col_2_increasing = col_positions[n_rows] < col_positions[(2*n_rows)-1]

    if row_1_constant:
        fill_order = 'horizontal'
    elif col_1_constant:
        fill_order = 'vertical'
    else:
        raise ValueError('Stitch layout could not be determined.')

    if fill_order == 'horizontal':
        if col_1_increasing and col_2_increasing:
            layout = 'horizontal'
        elif col_1_increasing or col_2_increasing:
            layout = 'zigzag_horizontal'
        else:
            raise ValueError('Stitch layout could not be determined.')
    elif fill_order == 'vertical':
        if row_1_increasing and row_2_increasing:
            layout = 'vertical'
        elif row_1_increasing or row_2_increasing:
            layout = 'zigzag_vertical'
        else:
            raise ValueError('Stitch layout could not be determined.')

    return layout


def calc_grid_coordinates_from_layout(stitch_dims, stitch_layout):
    '''Determines the position of each image in the stitched mosaic image.

    Parameters
    ----------
    stitch_dims: Dict[str, int]
        number of rows ("n_rows") and number of columns ("n_cols")
        of the stitched mosaic image
    stitch_layout: str
        "horizontal", "zigzag_horizontal", "vertical", or "zigzag_vertical"

    Returns
    -------
    List[Tuple[int]]
        pair of zero-based "row" (y) and "column" (x) position indices for each
        individual image in the stitched mosaic image in the order of
        acquisition, i.e. sorted according to image *site*

    Raises
    ------
    TypeError
        when `stitch_layout` doesn't have type string
    ValueError
        when `stitch_layout` is not in the set of the possible options
    '''
    layout_options = {
        'horizontal', 'zigzag_horizontal', 'vertical', 'zigzag_vertical'
    }
    if not isinstance(stitch_layout, basestring):
        raise TypeError('Layout must have type string.')
    if stitch_layout not in layout_options:
        raise ValueError(
            'Layout must be one of the following options:\n"%s"'
            % '", "'.join(layout_options)
        )

    cols = []
    rows = []
    if 'horizontal' in stitch_layout:
        for i in xrange(stitch_dims[0]):  # loop over rows
            if i % 2 and 'zigzag' in stitch_layout:
                # Reverse order of sites in columns every other iteration
                cols += range(stitch_dims[1]-1, -1, -1)
            else:
                # Preserve order of sites in columns
                cols += range(0, stitch_dims[1], 1)
            rows += [i for x in range(stitch_dims[1])]
    elif 'vertical' in stitch_layout:
        for i in xrange(stitch_dims[1]):  # loop over columns
            if i % 2 and 'zigzag' in stitch_layout:
                # Reverse order of sites in rows every other iteration
                rows += range(stitch_dims[0]-1, -1, -1)
            else:
                # Preserve order of sites in rows
                rows += range(0, stitch_dims[0], 1)
            cols += [i for x in range(stitch_dims[0])]
    return zip(rows, cols)


def calc_grid_coordinates_from_positions(stage_positions, n,
        reverse_rows=False, reverse_columns=False):
    '''Calculates the relative position of each image within the acquisition
    grid. The coordinates are one-based to be consistent with the OME data model.

    Parameters
    ----------
    stage_positions: List[Tuple[float]]
        absolute microscope stage positions
    n: int
        number of expected grid coordinates
    reverse_rows: bool, optional
        sort positions along row dimension in descending order
    reverse_columns: bool, optional
        sort positions along column dimension in descending order

    Note
    ----
    Since stage positions may not be identical for different channels acquired
    at the same site, the values are divided by 10 and then rounded (converted
    to integers).

    Returns
    -------
    List[Tuple[int]]
        relative positions (zero-based coordinates) within the grid
    '''
    # Calculate the spread along each dimension to determine the major stitch
    # axis.
    coordinates = np.array(stage_positions)
    if reverse_rows:
        coordinates[:, 0] *= -1
    if reverse_columns:
        coordinates[:, 1] *= -1

    # Caluculate centroids for each grid position
    model = KMeans(n_clusters=n)
    model.fit(coordinates)
    centroids = model.cluster_centers_
    indices = model.labels_

    # Determine grid dimensions: consider all possible splits and select the
    # one that fits best given the spread of provided absolute coordinate values
    spread = np.std(centroids, axis=0)
    splits = list()
    for i in range(2, n):
        div = n / float(i)
        if div % 1 == 0:
            splits.append((i, int(div)))
    splits = np.array(splits)
    if spread[0] > spread[1]:
        splits = splits[splits.shape[0]/2:, :]
    else:
        if splits.shape[0] == 1:
            splits = splits[splits.shape[0]/2:, :]
        else:
            splits = splits[0:splits.shape[0]/2, :]
    cost = splits[:, 0] / splits[:, 1].astype(float) - spread[0] / spread[1]
    best_fit_index = np.where(cost == np.min(cost))[0][0]
    rows, cols = splits[best_fit_index]
    logger.info('calculated stitch dimensions: %d x %d', rows, cols)

    # Assign relative grid coordinates to each absolute stage position
    row_edges = np.histogram(coordinates[:, 0], bins=rows)[1][:-1]
    col_edges = np.histogram(coordinates[:, 1], bins=cols)[1][:-1]
    positions = np.zeros(coordinates.shape, int)
    for i, (r, c) in enumerate(coordinates):
        row_index = np.where(row_edges <= r)[0]
        col_index = np.where(col_edges <= c)[0]
        positions[i, 0] = row_index[-1]
        positions[i, 1] = col_index[-1]

    return zip(*positions.T)
