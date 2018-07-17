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
'''Jterator module for measuring 3D morphology features.'''
import collections
import jtlib.features
import logging
import numpy as np
import pandas as pd

VERSION = '0.0.4'

Output = collections.namedtuple('Output', ['measurements', 'figure'])

logger = logging.getLogger(__name__)


class Morphology3D(jtlib.features.Features):
    '''Class for calculating 3D morphology statistics, such as volume
    and surface area of segmented objects.
    '''

    def __init__(self, label_image, intensity_image, pixel_size, z_step):
        '''
        Parameters
        ----------
        label_image: numpy.ndarray[numpy.int32]
            labeled image encoding objects (connected pixel components)
            for which features should be extracted
        intensity_image: numpy.ndarray[numpy.uint16 or numpy.uint8]
            grayscale image encoding the `height` as pixel intensity
            from which 3D morphology features should be extracted
        '''
        super(Morphology3D, self).__init__(label_image, intensity_image)
        self.pixel_size = pixel_size
        self.z_step = z_step

    @property
    def _feature_names(self):
        return ['max_height', 'mean_height', 'volume_pL',
                'lower_surface_area', 'upper_surface_area',
                'total_surface_area']

    def upper_surface_area(self, obj):
        '''Calculates the upper surface area of each object from the
        `volume_image`, using linear algebraic methods.
        '''
        # Transform z-coordinates using z-step size
        obj = obj.astype(np.float) * self.z_step
        area = 0

        # Iterate over all pixels
        for ix in range(obj.shape[0] - 1):
            for iy in range(obj.shape[1] - 1):
                # Find vertices
                v0 = np.array([self.pixel_size * ix,
                               self.pixel_size * iy,
                               obj[ix, iy]], np.double)
                v1 = np.array([self.pixel_size * (ix + 1),
                               self.pixel_size * iy,
                               obj[ix + 1, iy]], np.double) - v0
                v2 = np.array([self.pixel_size * ix,
                               self.pixel_size * (iy + 1),
                               obj[ix, iy + 1]], np.double) - v0
                v3 = np.array([self.pixel_size * (ix + 1),
                               self.pixel_size * (iy + 1),
                               obj[ix + 1, iy + 1]], np.double) - v0

                # Check all vertices are inside the object
                if not (np.isnan(v1)[2] or np.isnan(v2)[2] or np.isnan(v3)[2]):
                    # Add area of triangles to total
                    area += (np.linalg.norm(np.cross(v1, v3)) +
                             np.linalg.norm(np.cross(v2, v3))) / 2.0
        return area

    def extract(self):
        '''Extracts 3D morphology features by measuring pixel values
        within each object region in the `intensity_image`.

        Returns
        -------
        pandas.DataFrame
            extracted feature values for each object in `label_image`
        '''
        # Create an empty dataset in case no objects were detected
        logger.info('extract 3D morphology features')
        features = list()
        for obj in self.object_ids:
            mask = self.get_object_mask_image(obj)
            img = self.get_object_intensity_image(obj)

            # Set all non-object pixels to NaN
            img_nan = img.astype(np.float)
            img_nan[~mask] = np.nan

            # Calculate region properties and upper surface area
            region = self.object_properties[obj]
            lower_surface_area = region.area * self.pixel_size * self.pixel_size
            upper_surface_area = self.upper_surface_area(img_nan)
            values = [
                region.max_intensity * self.z_step,
                region.mean_intensity * self.z_step,
                (np.nansum(img_nan) * self.pixel_size *
                    self.pixel_size * self.z_step / 1000.0),
                lower_surface_area,
                upper_surface_area,
                lower_surface_area + upper_surface_area
            ]
            features.append(values)
        return pd.DataFrame(
            features, columns=self.names, index=self.object_ids)


def main(extract_objects, assign_objects, intensity_image,
         pixel_size=0.1625, z_step=0.25, plot=False):
    '''Measures 3D morphology features for objects in `extract_objects`
    based on grayscale values in `intensity_image` and assigns them to
    `assign_objects`.

    Parameters
    ----------
    extract_objects: numpy.ndarray[int32]
        label image with objects for which features should be extracted
    assign_objects: nu0mpy.ndarray[int32]
        label image with objects to which extracted features should be assigned
    intensity_image: numpy.ndarray[unit8 or uint16]
        grayscale image from which features should be extracted
    pixel_size: float
        x-y dimension of pixel in micrometres (default: ``0.1625`` for
        40x Yokogawa CellVoyager)
    z_step: float
        distance between consecutive z-planes in micrometres (default
        ``0.25``)
    plot: bool, optional
        whether a plot should be generated (default: ``False``)

    Returns
    -------
    jtmodules.measure_volume_image.Output[Union[List[pandas.DataFrame], str]]

    See also
    --------
    :class:`Morphology3D`
    '''

    f = Morphology3D(
        label_image=extract_objects,
        intensity_image=intensity_image,
        pixel_size=pixel_size,
        z_step=z_step,
    )

    f.check_assignment(assign_objects, aggregate=False)
    measurements = [f.extract()]

    if plot:
        figure = f.plot()
    else:
        figure = str()

    return Output(measurements, figure)
