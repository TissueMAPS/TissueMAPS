import numpy as np


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
    '''
    if stitch_major_axis == 'vertical':
        decent = True
    else:
        decent = False

    tmpI = np.arange((int(np.sqrt(n_sites)) - 5),
                     (int(np.sqrt(n_sites)) + 5))
    tmpII = np.matrix(tmpI).conj().T * np.matrix(tmpI)
    (a, b) = np.where(np.triu(tmpII) == n_sites)
    stitch_dims = sorted([abs(tmpI[a[0]]), abs(tmpI[b[0]])], reverse=decent)
    return (stitch_dims[0], stitch_dims[1])


def calc_stitch_dimensions(stage_positions):
    '''
    Determine stitch dimensions from stage positions.

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
    '''
    Determine the stitch layout of the mosaic image, i.e. in which order
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

    column_1_constant = col_positions[0] == col_positions[n_rows-1]
    column_1_increasing = row_positions[0] < row_positions[n_rows-1]
    column_2_increasing = row_positions[n_rows] < row_positions[(2*n_rows)-1]

    if row_1_constant:
        fill_order = 'horizontal'
    elif column_1_constant:
        fill_order = 'vertical'
    else:
        raise ValueError('Stitch layout could not be determined.')

    if fill_order == 'horizontal':
        if column_1_increasing and column_2_increasing:
            layout = 'horizontal'
        elif column_1_increasing or column_2_increasing:
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


def calc_grid_coordinates_from_positions(stage_positions,
                                         reverse_rows=False,
                                         reverse_columns=False):
    '''
    Calculate the relative position of each image within the acquisition grid.
    The coordinates are one-based to be consistent with the OME data model.

    Parameters
    ----------
    stage_positions: List[Tuple[float]]
        absolute microscope stage positions
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

    TODO
    ----
    How to deal with reversing of axes in an automated way?
    '''
    # The stage positions may not be identical between different
    # channels acquired at the same site, so we round them.
    rounded_positions = [(int(p[0]/10), int(p[1]/10)) for p in stage_positions]

    # Determine unique stage positions.
    unique_positions = list(set(rounded_positions))
    unique_indices = [unique_positions.index(p) for p in rounded_positions]

    # Calculate the relative coordinates for each unique stage position.
    positions = np.array(unique_positions)
    row_positions = np.unique(positions[:, 0])
    col_positions = np.unique(positions[:, 1])

    if reverse_rows:
        row_positions = row_positions[::-1]
    if reverse_columns:
        col_positions = col_positions[::-1]

    unique_coordinates = [tuple() for x in xrange(len(unique_positions))]
    for i, r in enumerate(row_positions):
        for j, c in enumerate(col_positions):
            pos = np.array((r, c))
            pos_index = np.where(np.all(positions == pos, axis=1))
            for ix in pos_index:
                if len(ix) == 0:
                    continue
                unique_coordinates[ix[0]] = (i, j)

    # Map the unique coordinates back.
    coordinates = [unique_coordinates[i] for i in unique_indices]

    return coordinates
