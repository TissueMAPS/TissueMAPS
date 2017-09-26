# Copyright 2016 Markus D. Herrmann, University of Zurich
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#     http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import numpy as np
import pandas as pd
import math
import mahotas as mh
from skimage import measure, morphology


def rescale_to_8bit(im, lower=0, upper=100):
    '''Maps pixel values of an image from the range between a lower and an
    upper quantile to the range [0,255].

    Parameters
    ----------
    im: numpy.ndarray[numpy.uint16]
        16-bit grayscale image
    lower: float, optional
        quantile to define lower bound of range (default: ``0``)
    upper: float, optional
        quantile to define upper bound of range (default: ``100``)

    Returns
    -------
    numpy.ndarray[numpy.uint8]
        rescaled 8-bit grayscale image
    '''
    lower_bound = int(np.percentile(im, lower))
    upper_bound = int(np.percentile(im, upper))
    lut = np.concatenate([
        np.zeros(lower_bound, dtype=np.uint16),
        np.linspace(0, 255, upper_bound - lower_bound).astype(np.uint16),
        np.ones(2**16 - upper_bound, dtype=np.uint16) * 255
    ])
    return lut[im].astype(np.uint8)


def extract_bbox(im, bbox, pad=0):
    '''Extracts a subset of pixels from a 2D image defined by a given
    bounding box.

    Parameters
    ----------
    im: numpy.ndarray
        image
    bbox: List[int]
        bounding box coordinates
    pad: int, optional
        pad extracted image with n lines of zero values along each dimension
        (default: ``0``)

    Returns
    -------
    numpy.ndarray
        extracted pixels

    Note
    ----
    The bounding box can be created by :meth:`mahotas.labeled.bbox`.
    '''
    cropped_im = im[bbox[0]:bbox[1], bbox[2]:bbox[3]]
    if pad:
        cropped_im = np.lib.pad(
            cropped_im, (pad, pad), 'constant', constant_values=(0)
        )
    return cropped_im


def get_border_ids(im):
    '''Determines the ids (labels) of objects at the border of an image.

    Parameters
    ----------
    im: numpy.ndarray[numpy.int32]
        labeled image

    Returns
    -------
    List[int]
        object ids
    '''
    borders = [
        np.unique(im[0, :]),
        np.unique(im[-1, :]),
        np.unique(im[:, 0]),
        np.unique(im[:, -1])
    ]
    border_ids = list(reduce(set.union, map(set, borders)).difference({0}))
    object_ids = np.unique(im[im != 0])
    return [i for i in object_ids if i in border_ids]


def label(im, n=4):
    '''Labels connected components in an image.

    Parameters
    ----------
    im: numpy.ndarray[numpy.bool]
        binary image that should be labeled
    n: int, optional
        neighbourhood (default: ``4``, choices: ``{4, 8}``)

    Returns
    -------
    numpy.ndarray[int]
        labeled image

    Raises
    ------
    ValueError
        when `n` is not ``4`` or ``8``

    '''
    if n not in {4, 8}:
        raise ValueError('Neighbourhood must be 4 or 8.')
    if n == 8:
        strel = np.ones((3, 3), bool)
        labeled_image, n_objects = mh.label(im>0, strel)
    else:
        labeled_image, n_objects = mh.label(im>0)
    return labeled_image


def downsample(im, bins):
    '''
    Murphy et al. 2002
    "Robust Numerical Features for Description and Classification of
    Subcellular Location Patterns in Fluorescence Microscope Images"

    Parameters
    ----------
    im: numpy.ndarray
        grayscale image
    bins: int
        number of bins

    Returns
    -------
    numpy.ndarray
        downsampled image
    '''
    if bins != 256:
        min_val = im.min()
        max_val = im.max()
        ptp = max_val - min_val
        if ptp:
            return np.array((im-min_val).astype(float) * bins/ptp,
                            dtype=np.uint8)
        else:
            return np.array(im.astype(float), dtype=np.uint8)


def sort_coordinates_counter_clockwise(coordinates):
    '''Sorts *y*, *x* coordinates values in counter clockwise order.

    Parameters
    ----------
    coordinates: numpy.ndarray[int]
        nx2 array of coordinate values, where each row represents a point
        and the 1. column are the *y* values and the 2. column the *x* values

    Returns
    -------
    numpy.ndarray[np.int64]
        sorted array
    '''
    mean_y = np.sum(coordinates[:, 0]) / coordinates.shape[0]
    mean_x = np.sum(coordinates[:, 1]) / coordinates.shape[0]

    def calc_angle(c):
        # Adapted form stackoverflow question #1709283
        return (
            (math.atan2(c[0] - mean_y, c[1] - mean_x) + 2 * math.pi)
            % (2*math.pi)
        )

    angles = np.apply_along_axis(calc_angle, axis=1, arr=coordinates)
    sorted_coordinates = pd.DataFrame({
        'y': coordinates[:, 0].astype(np.int64),
        'x': coordinates[:, 1].astype(np.int64),
        'order': angles
    }).sort_values(by='order')
    return sorted_coordinates[['y', 'x']].values
