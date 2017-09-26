# Copyright 2017 Scott Berry, University of Zurich
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
'''Jterator module for extracting a volume image from a 3D stack'''
import collections
import logging
import numpy as np
from jtlib.segmentation import detect_blobs

logger = logging.getLogger(__name__)

VERSION = '0.1.0'

Output = collections.namedtuple('Output', ['volume_image', 'figure'])


def array_to_coordinate_list(array):
    '''Convert a 2D array representation of points in 3D
    to a list of x,y,z coordinates'''
    points = []
    for ix in range(array.shape[0]):
        for iy in range(array.shape[1]):
            if (array[ix, iy] > 0):
                points.append((ix, iy, array[ix, iy]))
    return points


def subsample_coordinate_list(points, num):
    subpoints = np.array(points)[np.linspace(
        start=0, stop=len(points), endpoint=False,
        num=num, dtype=np.uint32)]
    return list(map(tuple, subpoints))


def plane(x, y, params):
    '''Compute z-coordinate of plane in 3D'''
    a, b, c = params
    z = (a * x) + (b * y) + c
    return z


# Least squares error estimate
def squared_error(params, points):
    '''Compute the sum of squared residuals'''
    result = 0
    for (x, y, z) in points:
        plane_z = plane(x, y, params)
        diff = abs(plane_z - z)
        result += diff**2
    return result


def fit_plane(points):
    '''Fit a plane to the 3D beads surface'''
    import scipy.optimize
    import functools

    fun = functools.partial(squared_error, points=points)
    params0 = [0, 0, 0]
    return scipy.optimize.minimize(fun, params0)


def locate_in_3D(image, mask, bin_size=1, surface_plane_params=[0, 0, 0]):
    '''From a 2D array ``mask``, find the brightest
    corresponding point in 3D ``image``'''

    def rebin(arr, new_shape):
        '''Rebin 2D array arr to shape new_shape by averaging.'''
        shape = (new_shape[0], arr.shape[0] // new_shape[0],
                 new_shape[1], arr.shape[1] // new_shape[1])
        return arr.reshape(shape).mean(-1).mean(1)

    if bin_size > 1:
        image_binned = np.zeros(
            (image.shape[0] / 2, image.shape[1] / 2, image.shape[2]),
            dtype=np.uint16
        )
        for iz in range(image_binned.shape[2]):
            image_binned[:, :, iz] = rebin(
                image[:, :, iz],
                np.shape(image_binned[:, :, iz])
            )
    else:
        image_binned = image

    x, y, z = [], [], []
    for ix in range(image.shape[0]):
        for iy in range(image.shape[1]):
            if mask[ix, iy] > 0:
                max_pos = np.argmax(
                    image_binned[int(ix / bin_size), int(iy / bin_size), :]
                )
                height = int(
                    max_pos - plane(ix, iy, surface_plane_params)
                )
                if height > 0:
                    x.append(ix)
                    y.append(iy)
                    z.append(height)

    coords = collections.namedtuple("coords", ["x", "y", "z"])
    return coords(x=x, y=y, z=z)


def interpolate_surface(coords, output_shape, method='linear'):
    '''Given a set of coordinates (not necessarily on a grid), an
    interpolation is returned as a numpy array'''
    from scipy.interpolate import griddata

    xy = np.column_stack((coords.x, coords.y))
    xv, yv = np.meshgrid(
        range(output_shape[0]),
        range(output_shape[1])
    )
    if method == 'nearest':
        interpolate = griddata(
            xy, np.array(coords.z), (xv, yv), method='nearest', rescale=False
        )
    elif method == 'cubic':
        interpolate = griddata(
            xy, np.array(coords.z), (xv, yv), method='cubic', rescale=False
        )
    elif method == 'linear':
        interpolate = griddata(
            xy, np.array(coords.z), (xv, yv), method='linear', rescale=False
        )

    return interpolate.T


def main(image, mask, threshold=150, bead_size=2, superpixel_size=4,
         close_surface=False, close_disc_size=8, plot=False):
    '''Converts an image stack with labelled cell surface to a cell
    `volume` image

    Parameters
    ----------
    image: numpy.ndarray[Union[numpy.uint8, numpy.uint16]]
        grayscale image in which beads should be detected (3D)
    mask: numpy.ndarray[Union[numpy.int32, numpy.bool]]
        binary or labeled image of cell segmentation (2D)
    threshold: int, optional
        intensity of bead (default: ``150``)
    bead_size: int, optional
        minimal size of bead (default: ``2``)
    superpixel_size: int, optional
        size of superpixels for searching the 3D position of a bead
    close_surface: bool, optional
        whether the interpolated surface should be morphologically closed
    close_disc_size: int, optional
        size in pixels of the disc used to morphologically close the
        interpolated surface
    plot: bool, optional
        whether a plot should be generated (default: ``False``)

    Returns
    -------
    jtmodules.generate_volume_image.Output
    '''

    n_slices = image.shape[-1]
    logger.debug('input image has size %d in last dimension', n_slices)

    logger.debug('mask beads inside cell')
    beads_outside_cell = np.copy(image)
    for iz in range(n_slices):
        beads_outside_cell[mask > 0, iz] = 0

    logger.debug('search for 3D position of beads outside cell')
    slide = np.argmax(beads_outside_cell, axis=2)
    slide[slide > np.percentile(slide[mask == 0], 20)] = 0

    logger.debug('determine surface of slide')
    slide_coordinates = array_to_coordinate_list(slide)
    bottom_surface = fit_plane(subsample_coordinate_list(
        slide_coordinates, 2000)
    )

    logger.debug('detect_beads in 2D')
    mip = np.max(image, axis=-1)
    try:
        # TODO: use LOG filter???
        beads, beads_centroids = detect_blobs(
            image=mip, mask=np.invert(mask > 0), threshold=threshold,
            min_area=bead_size
        )
    except:
        logger.warn('detect_blobs failed, returning empty volume image')
        volume_image = np.zeros(shape=mask.shape, dtype=image.dtype)
        figure = str()
        return Output(volume_image, figure)

    n_beads = np.count_nonzero(beads_centroids)
    logger.info('found %d beads on cells', n_beads)

    if n_beads == 0:
        logger.warn('empty volume image')
        volume_image = np.zeros(shape=mask.shape, dtype=image.dtype)
    else:
        logger.debug('locate beads in 3D')
        beads_coords_3D = locate_in_3D(
            image=image, mask=beads_centroids,
            bin_size=superpixel_size
        )

        logger.info('interpolate cell surface')
        volume_image = interpolate_surface(
            coords=beads_coords_3D,
            output_shape=np.shape(image[:, :, 1]),
            method='linear'
        )

        volume_image = volume_image.astype(image.dtype)

        if (close_surface is True):
            import mahotas as mh
            logger.info('morphological closing of cell surface')
            volume_image = mh.close(volume_image,
                                    Bc=mh.disk(close_disc_size))
        volume_image[mask == 0] = 0

    if plot:
        logger.debug('convert bottom surface plane to image for plotting')
        bottom_surface_image = np.zeros(slide.shape, dtype=np.uint8)
        for ix in range(slide.shape[0]):
            for iy in range(slide.shape[1]):
                bottom_surface_image[ix, iy] = plane(
                    ix, iy, bottom_surface.x)

        logger.info('create plot')
        from jtlib import plotting
        plots = [
            plotting.create_intensity_image_plot(
                mip, 'ul', clip=True
            ),
            plotting.create_intensity_image_plot(
                bottom_surface_image, 'll', clip=True
            ),
            plotting.create_intensity_image_plot(
                volume_image, 'ur', clip=True
            )
        ]
        figure = plotting.create_figure(
            plots, title='Convert stack to volume image'
        )
    else:
        figure = str()

    return Output(volume_image, figure)
