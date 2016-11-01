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
'''Jterator module for registering objects, which will allow taking measurements
of the objects and persist them on disk.
'''
import collections
import logging

logger = logging.getLogger(__name__)

VERSION = '0.0.1'

Output = collections.namedtuple('Output', ['objects', 'as_polygons'])


def main(label_image, as_polygons=True):
    '''Registeres segmented objects in a labeled image for use by other
    (measurement) modules downstream in the pipeline.

    Parameters
    ----------
    label_image: numpy.ndarray[int32]
        labeled image where pixel values encode objects IDs
    as_polygons: boolean, optional
        whether objects should be represented as polygons;
        if ``False`` they will be represented as lines (default: ``True``)

    Returns
    -------
    jtmodules.register_objects.Output
    '''
    return Output(label_image, as_polygons)
