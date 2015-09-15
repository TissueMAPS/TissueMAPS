import re
import numpy as np


def calc_sites_number(image_files, regexp):
    '''
    Determine the maximum position, i.e. the total number of image acquisition
    sites from a set of image filenames.

    Parameters
    ----------
    image_files: List[str]
        image filenames
    regexp: str
        named regular expression containing a symbolic group name "site"
        (see `re module <https://docs.python.org/2/library/re.html>`_ for
         more information on regular expressions)

    Returns
    -------
    int
        number of image acquisition sites

    Raises
    ------
    ValueError
        when `regexp` doesn't match `image_files`
    '''
    image_sites = [re.search(regexp, f) for f in image_files]
    if not image_sites:
        raise ValueError('Regular expression doesn\'t match filenames')
    image_sites = [int(s.group('site')) for s in image_sites]
    n_sites = max(image_sites)
    return n_sites


def guess_stitch_dimensions(n_sites, more_rows_than_columns=True):
    '''
    Simple algorithm to guess correct dimensions of a stitched mosaic image.

    Parameters
    ----------
    n_sites: int
        total number of sites (individual images) in the stitched mosaic image
    more_rows_than_columns: bool, optional
        whether there are more rows than columns (default)

    Returns
    -------
    Tuple[int]
        number of rows and columns of the stitched mosaic image
    '''
    if more_rows_than_columns:
        decent = True
    else:
        decent = False

    tmpI = np.arange((int(np.sqrt(n_sites)) - 5),
                     (int(np.sqrt(n_sites)) + 5))
    tmpII = np.matrix(tmpI).conj().T * np.matrix(tmpI)
    (a, b) = np.where(np.triu(tmpII) == n_sites)
    stitch_dims = sorted([tmpI[a[0]], tmpI[b[0]]], reverse=decent)
    return (stitch_dims[0], stitch_dims[1])


def calc_stitch_dimensions(stage_positions):
    '''
    Determine stitch dimensions from stage positions.

    Parameters
    ----------
    stage_positions: Tuple[float]
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


def calc_image_position(stitch_dims, stitch_layout):
    '''
    Determine the position of each image in the stitched mosaic image.

    Parameters
    ----------
    stitch_dims: Dict[str, int]
        number of rows ("n_rows") and number of columns ("n_cols")
        of the stitched mosaic image
    stitch_layout: str
        "horizontal", "zigzag_horizontal", "vertical", or "zigzag_vertical"

    Returns
    -------
    Tuple[int]
        pair of one-based "row" (y) and "column" (x) position indices for each
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
                cols += range(stitch_dims[1], 0, -1)
            else:
                # Preserve order of sites in columns
                cols += range(1, stitch_dims[1]+1, 1)
            rows += [i+1 for x in range(stitch_dims[1])]
    elif 'vertical' in stitch_layout:
        for i in xrange(stitch_dims[1]):  # loop over columns
            if i % 2 and 'zigzag' in stitch_layout:
                # Reverse order of sites in rows every other iteration
                rows += range(stitch_dims[0], 0, -1)
            else:
                # Preserve order of sites in rows
                rows += range(1, stitch_dims[0]+1, 1)
            cols += [i+1 for x in range(stitch_dims[0])]
    return zip(rows, cols)
