# Copyright (C) 2016 University of Zurich.
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
'''Jterator module for labeling connected pixel components.'''
import logging
import numpy as np
import collections
import mahotas as mh
from jtlib.utils import label

logger = logging.getLogger(__name__)

VERSION = '0.1.0'

Output = collections.namedtuple('Output', ['label_image', 'figure'])


def main(mask, connectivity=8, plot=False):
    '''Labels objects in a binary image, i.e. assigns to all pixels of a
    connected component an identifier number that is unique for each object
    in the image.

    Parameters
    ----------
    mask: numpy.ndarray[Union[numpy.bool, numpy.int32]]
        binary image that should labeled
    connectivity: int, optional
        whether a diagonal (``4``) or square (``8``) neighborhood should be
        considered (default: ``8``, options: ``{4, 8}``)
    plot: bool, optional
        whether a plot should be generated (default: ``False``)

    Returns
    -------
    jtmodules.label.Output[Union[numpy.ndarray, str]]

    Note
    ----
    If `mask` is not binary, it will be binarized, i.e. pixels will be set to
    ``True`` if values are greater than zero and ``False`` otherwise.
    '''
    mask = mask > 0
    label_image = label(mask, connectivity)

    n = len(np.unique(label_image)[1:])
    logger.info('identified %d objects', n)

    if plot:
        from jtlib import plotting
        plots = [
            plotting.create_mask_image_plot(mask, 'ul'),
            plotting.create_mask_image_plot(label_image, 'ur')
        ]
        figure = plotting.create_figure(plots, title='Labeled image')
    else:
        figure = str()

    return Output(label_image, figure)
