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
'''Jterator module for relabeling connected pixel components.'''
import logging
import numpy as np
import collections
import mahotas as mh


logger = logging.getLogger(__name__)

VERSION = '0.0.1'

Output = collections.namedtuple('Output', ['relabeled_image', 'figure'])


def main(label_image, plot=False):
    '''Relabels objects in a label image such that the total number of objects
    is preserved.

    Parameters
    ----------
    label_image: numpy.ndarray[numpy.int32]
        label image that should relabeled
    plot: bool, optional
        whether a plot should be generated (default: ``False``)

    Returns
    -------
    jtmodules.relabel.Output[Union[numpy.ndarray, str]]

    '''
    relabeled_image = mh.labeled.relabel(label_image)[0]

    if plot:
        from jtlib import plotting
        plots = [
            plotting.create_mask_image_plot(label_image, 'ul'),
            plotting.create_mask_image_plot(relabeled_image, 'ur')
        ]
        figure = plotting.create_figure(plots, title='Relabeled image')
    else:
        figure = str()

    return Output(relabeled_image, figure)

