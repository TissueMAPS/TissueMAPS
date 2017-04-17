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
'''Jterator module for registering objects. Registration allows subsequent
measurements of the objects (feature extraction) and automatically persist them
on disk.
'''
import collections
import logging
from jtlib.utils import label

logger = logging.getLogger(__name__)

VERSION = '0.1.0'

Output = collections.namedtuple('Output', ['objects'])


def main(mask):
    '''Registers objects (connected pixel components) in an image for use by
    other (measurement) modules downstream in the pipeline. In case a binary
    mask is provided the image is automatically labeled.

    Parameters
    ----------
    mask: numpy.ndarray[Union[numpy.bool, numpy.int32]]
        binary or labeled mask

    Returns
    -------
    jtmodules.register_objects.Output

    See also
    --------
    :class:`tmlib.workflow.jterator.handles.SegmentedObjects`
    '''
    if mask.dtype == 'bool':
        label_image = label(mask)
    else:
        label_image = mask
    return Output(label_image)
