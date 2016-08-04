import numpy as np
from scipy.cluster.vq import kmeans
import itertools

from tmlib.errors import MetadataError


def guess_stitch_dimensions(n_sites, stitch_major_axis='vertical'):
    '''
    Simple algorithm to guess correct dimensions of a stitched mosaic image.

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
    ValueError
        when value of `stitch_major_axis` is neither ``"horizontal"`` nor
        ``"vertical"``
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

    # TODO: this could be further generalized
    if n_sites > 100:
        n = 10
    else:
        n = 5
    tmpI = np.arange((int(np.sqrt(n_sites)) - n), (int(np.sqrt(n_sites)) + n))
    tmpII = np.matrix(tmpI).conj().T * np.matrix(tmpI)
    (a, b) = np.where(np.triu(tmpII) == n_sites)
    if len(a) == 0 and len(b) == 0:
        raise IndexError(
            'Dimensions of stitched overview could not be determined.'
        )
    stitch_dims = sorted([abs(tmpI[a[0]]), abs(tmpI[b[0]])], reverse=decent)
    return (stitch_dims[0], stitch_dims[1])


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
        'horizontal',
        'zigzag_horizontal',
        'vertical',
        'zigzag_vertical'
    }
    if not isinstance(stitch_layout, basestring):
        raise TypeError('Layout must have type string.')
    if stitch_layout not in layout_options:
        raise ValueError('Layout must be one of the following options:\n"%s"'
                         % '", "'.join(layout_options))

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
                                         reverse_rows=False,
                                         reverse_columns=False):
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
    spread = np.max(coordinates, axis=0) - np.min(coordinates, axis=0)
    options = np.array(['vertical', 'horizontal'])
    # Guess the stitch dimensions.
    index = np.where(spread == np.max(spread))[0][0]
    dims = guess_stitch_dimensions(n, options[index])
    positions = np.array([
        p for p in itertools.product(range(dims[0]), range(dims[1]))
    ])

    if reverse_rows:
        coordinates[:, 0] *= -1
    if reverse_columns:
        coordinates[:, 1] *= -1

    # Caluculate the centroids for each grid position.
    row_centroids, _ = kmeans(coordinates[:, 0], dims[0])
    col_centroids, _ = kmeans(coordinates[:, 1], dims[1])
    centroids = np.array([
        c for c in itertools.product(
            sorted(row_centroids), sorted(col_centroids)
        )
    ])

    grid_positions = list()
    indices = list()
    for c in coordinates:
        # Find the stage position that's closest to the centroid.
        distance = centroids - c
        closest = np.sum(np.abs(distance), axis=1)
        index = np.where(closest == np.min(closest))[0][0]
        pos = tuple(positions[index, :])
        grid_positions.append(pos)
        indices.append(index)

    if len(set(grid_positions)) != n:
        raise MetadataError(
            'Either the expected number of grid positions is incorrect or '
            'wrong stage positions were provided.'
        )
        # Or there is a bug in this code ;)
    return grid_positions
