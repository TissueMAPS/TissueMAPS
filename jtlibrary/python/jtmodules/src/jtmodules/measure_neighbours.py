# Copyright 2019 Scott Berry, University of Zurich
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
'''Jterator module for measuring neighbour features.'''
import collections
import jtlib.features
import logging
import numpy as np
import pandas as pd
import mahotas as mh
from scipy import ndimage as ndi

VERSION = '0.0.1'

Output = collections.namedtuple('Output', ['measurements', 'figure'])

logger = logging.getLogger(__name__)


class Neighbours(jtlib.features.Features):
    '''Class for calculating neighbour features.
    '''

    def __init__(self, label_image, neighbour_distance, touching_distance):
        '''
        Parameters
        ----------
        label_image: numpy.ndarray[numpy.int32]
            labeled image encoding objects (connected pixel components)
            for which features should be extracted
        '''
        super(Neighbours, self).__init__(label_image)
        self.neighbour_distance = neighbour_distance
        self.touching_distance = touching_distance

    @property
    def _feature_names(self):
        return ['Neighbours_Count', 'Neighbours_List', 'Fraction_Touching']

    def get_bbox_containing_neighbours(self, object_id, pad):
        '''Extracts the bounding box for a given object from
        :attr:`label_image <jtlib.features.Features.label_image>`.

        Returns
        -------
        numpy.ndarray[int32]
            label image for given object including surrounding objects
            of the same type
        '''
        bbox = self._bboxes[object_id]
        ymin = bbox[0] - pad if bbox[0] - pad > 0 else 0
        ymax = bbox[1] + pad if bbox[1] + pad < self.label_image.shape[0] else self.label_image.shape[0]
        xmin = bbox[2] - pad if bbox[2] - pad > 0 else 0
        xmax = bbox[3] + pad if bbox[3] + pad < self.label_image.shape[1] else self.label_image.shape[1]
        img = self.label_image[ymin:ymax, xmin:xmax]
        return img

    def extract(self):
        '''Extracts neighbour features.

        Returns
        -------
        pandas.DataFrame
            extracted feature values for each object in `label_image`
        '''
        # Create an empty dataset in case no objects were detected
        logger.info('extract neighbour features')
        features = list()

        for obj in self.object_ids:
            pad = max(self.neighbour_distance, self.touching_distance)
            object_image = self.get_bbox_containing_neighbours(obj,pad)

            # dilate the current object
            object_image_dilate = mh.dilate(
                object_image == obj,
                Bc=mh.disk(self.neighbour_distance))

            # mask the corresponding region of the label image
            object_image_mask = np.copy(object_image)
            object_image_mask[object_image_dilate == 0] = 0
            object_image_mask[object_image == obj] = 0
            neighbour_ids = np.unique(object_image_mask)
            unique_values = neighbour_ids[np.nonzero(neighbour_ids)].tolist()
            neighbour_count = len(unique_values)

            # save these unique values as a string
            if neighbour_count == 0:
                neighbour_string = '.'
            else:
                neighbour_string = '.'.join(str(x) for x in unique_values)

            # create an inverted image of the surrounding cells
            neighbours = np.zeros_like(object_image)
            for n in unique_values:
                neighbours += mh.dilate(object_image == n)

            # calculate the distance from each pixel of object to neighbours
            dist = ndi.morphology.distance_transform_edt(
                np.invert(neighbours > 0))

            # select perimeter pixels whose distance to neighbours is
            # less than threshold touching distance
            perimeter_image = mh.bwperim(object_image == obj)
            dist[perimeter_image == 0] = 0
            dist[dist > self.touching_distance] = 0

            fraction_touching = np.count_nonzero(dist) / float(np.count_nonzero(perimeter_image))

            values = [
                neighbour_count,
                neighbour_string,
                fraction_touching
            ]
            features.append(values)
        return pd.DataFrame(
            features, columns=self.names, index=self.object_ids)


def main(extract_objects, assign_objects, neighbour_distance, touching_distance, plot=False):
    '''Measures neighbour features for objects in `extract_objects`
     and assigns them to `assign_objects`.

    Parameters
    ----------
    extract_objects: numpy.ndarray[int32]
        label image with objects for which features should be extracted
    assign_objects: nu0mpy.ndarray[int32]
        label image with objects to which extracted features should be assigned
    neighbour_distance: integer
        distance in pixels between objects to be considered "neighbours"
    touching_distance: integer
        distance in pixels between objects to be considered "touching"

    Returns
    -------
    jtmodules.measure_neighbours.Output[Union[List[pandas.DataFrame], str]]

    See also
    --------
    :class:`Neighbours`
    '''

    f = Neighbours(
        label_image=extract_objects,
        neighbour_distance=neighbour_distance,
        touching_distance=touching_distance
    )

    f.check_assignment(assign_objects, aggregate=False)
    measurements = [f.extract()]

    if plot:
        figure = f.plot()
    else:
        figure = str()

    return Output(measurements, figure)
