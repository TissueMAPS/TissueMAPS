# TmLibrary - TissueMAPS library for distibuted image processing routines.
# Copyright (C) 2016  Markus D. Herrmann, University of Zurich and Robin Hafen
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
import numpy as np


def guess_stitch_dimensions(n_sites, stitch_major_axis='vertical'):
    '''
    Guess dimensions of a stitched mosaic image.

    Parameters
    ----------
    n_sites: int
        total number of image acquisition sites
    stitch_major_axis: str, optional
        ``"horizontal"``when there are more columns than rows
        and ``"vertical"`` otherwise (default: ``"vertical"``)

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
    stitch_dims = sorted([tmpI[a[0]], tmpI[b[0]]], reverse=decent)
    return (stitch_dims[0], stitch_dims[1])


def calc_image_coordinates_layout(stitch_dims, stitch_layout):
    '''
    Determine the position of each image in the stitched mosaic image,
    i.e. the overall acquisition grid.

    Parameters
    ----------
    stitch_dims: Dict[str, int]
        number of rows and number of columns of the stitched mosaic image
    stitch_layout: str
        the layout in which images were acquired and need to be stitched
        together: "horizontal", "zigzag_horizontal", "vertical", or
        "zigzag_vertical"

    Returns
    -------
    List[Tuple[int]]
        pair of one-based "row" (y) and "column" (x) position indices for each
        individual image in the stitched mosaic image in the order of
        acquisition, i.e. sorted according to image *site*

    Raises
    ------
    ValueError
        when `stitch_layout` is not in the set of the possible options
    '''
    layout_options = {
        'horizontal',
        'zigzag_horizontal',
        'vertical',
        'zigzag_vertical'
    }
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
