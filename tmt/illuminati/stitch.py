import numpy as np


def guess_stitch_dims(max_position, more_rows_than_columns=True):
    '''
    Simple algorithm to guess correct dimensions of a stitched mosaic image.

    Parameters
    ----------
    max_position: int
        maximum position in the stitched mosaic image
    more_rows_than_columns: bool, optional
        whether there are more rows than columns (default)

    Returns
    -------
    Dict[str, int]
        number of rows and columns of the stitched mosaic image
    '''
    if more_rows_than_columns:
        decent = True
    else:
        decent = False

    tmpI = np.arange((int(np.sqrt(max_position)) - 5),
                     (int(np.sqrt(max_position)) + 5))
    tmpII = np.matrix(tmpI).conj().T * np.matrix(tmpI)
    (a, b) = np.where(np.triu(tmpII) == max_position)
    stitch_dims = sorted([tmpI[a[0]], tmpI[b[0]]], reverse=decent)
    return (stitch_dims[0], stitch_dims[1])


def determine_stitch_dims(stage_positions):
    '''
    Determine stitch dimensions from stage positions.

    Parameters
    ----------
    stage_positions: Tuple[float]
        stage positions in row (x) and column (y) direction

    Returns
    -------
    Dict[str, int]
        number of rows and columns of the stitched mosaic image
    '''
    row_positions = [p[0] for p in stage_positions]
    col_positions = [p[1] for p in stage_positions]
    n_rows = len(set(row_positions))
    n_cols = len(set(col_positions))
    return (n_rows, n_cols)


def determine_stitch_layout(stitch_dims, stage_positions):
    '''
    Determine the stitch layout of the mosaic image, i.e. in which order
    individual images need to be stitched together.

    .. code-block:: python

        {
            "fill_order": str,   # either "vertical" or "horizontal"
            "zig_zag": bool
        }

    Parameters
    ----------
    stitch_dims: Dict[str, int]
        number of rows and columns of the stitched mosaic image
    stage_positions: Tuple[float]
        stage positions in row (x) and column (y) direction

    Returns
    -------
    Dict[str, str or bool]
        stitch layout
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
        raise Exception('Stitch layout could not be determined.')

    if fill_order == 'horizontal':
        if column_1_increasing and column_2_increasing:
            zig_zag = False
        elif column_1_increasing or column_2_increasing:
            zig_zag = True
    elif fill_order == 'vertical':
        if row_1_increasing and row_2_increasing:
            zig_zag = False
        elif row_1_increasing or row_2_increasing:
            zig_zag = True

    return {'fill_order': fill_order, 'zig_zag': zig_zag}


def determine_image_position(stitch_dims, zig_zag, fill_order):
    '''
    Determine the position of each image in the stitched mosaic image.

    Parameters
    ----------
    stitch_dims: Dict[str, int]
        number of rows ("n_rows") and number of columns ("n_cols")
        of the stitched mosaic image
    zig_zag: bool
        whether images were acquired in "ZigZag" mode
    fill_order: str
        "vertical" or "horizontal" acquisition

    Returns
    -------
    Tuple[int]
        pair of one-based "row" (y) and "column" (x) position indices for each
        individual image in the stitched mosaic image in the order of
        acquisition, i.e. sorted according to image *site*

    Raises
    ------
    ValueError
        when `fill_order` is not specified correctly
    '''
    cols = []
    rows = []
    if fill_order == 'horizontal':
        for i in xrange(stitch_dims[0]):  # loop over rows
            if i % 2 and zig_zag:
                # Reverse order of sites in columns every other iteration
                cols += range(stitch_dims[1], 0, -1)
            else:
                # Preserve order of sites in columns
                cols += range(1, stitch_dims[1]+1, 1)
            rows += [i+1 for x in range(stitch_dims[1])]
    elif fill_order == 'vertical':
        for i in xrange(stitch_dims[1]):  # loop over columns
            if i % 2 and zig_zag:
                # Reverse order of sites in rows every other iteration
                rows += range(stitch_dims[0], 0, -1)
            else:
                # Preserve order of sites in rows
                rows += range(1, stitch_dims[0]+1, 1)
            cols += [i+1 for x in range(stitch_dims[0])]
    else:
        raise ValueError('Fill order must be either "horizontal" or '
                         '"vertical"')
    return zip(rows, cols)
