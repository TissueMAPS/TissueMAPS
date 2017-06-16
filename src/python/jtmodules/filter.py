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
'''Jterator module for filtering objects based on one of the
:const:`SUPPORTED_FEATURES <jtmodules.filter_objects.SUPPORTED_FEATURES>`.'''
import logging
import numpy as np
import mahotas as mh
import collections
from jtlib import utils
from jtlib.features import Morphology, create_feature_image


VERSION = '0.1.1'

logger = logging.getLogger(__name__)

Output = collections.namedtuple('Output', ['filtered_mask', 'figure'])

SUPPORTED_FEATURES = {'area', 'eccentricity', 'circularity', 'convexity'}


def main(mask, feature, lower_threshold=None, upper_threshold=None, plot=False):
    '''Filters objects (connected components) based on the specified
    value range for a given `feature`.

    Parameters
    ----------
    mask: numpy.ndarray[Union[numpy.bool, numpy.int32]]
        image that should be filtered
    feature: str
        name of the feature based on which the image should be filtered
        (options: ``{"area", "eccentricity", "circularity", "convecity"}``)
    lower_threshold:
        minimal `feature` value objects must have
        (default: ``None``; type depends on the chosen `feature`)
    upper_threshold:
        maximal `feature` value objects must have
        (default: ``None``; type depends on the chosen `feature`)
    plot: bool, optional
        whether a plot should be generated (default: ``False``)

    Returns
    -------
    jtmodules.filter_objects.Output

    Raises
    ------
    ValueError
        when both `lower_threshold` and `upper_threshold` are ``None``
    ValueError
        when value of `feature` is not one of the supported features

    '''
    if lower_threshold is None and upper_threshold is None:
        raise ValueError(
            'Argument "lower_threshold" or "upper_threshold" must be provided. '
        )
    if feature not in SUPPORTED_FEATURES:
        raise ValueError(
            'Argument "feature" must be one of the following: "%s".'
            % '", "'.join(SUPPORTED_FEATURES)
        )

    name = 'Morphology_{0}'.format(feature.capitalize())

    labeled_image = mh.label(mask > 0)[0]
    f = Morphology(labeled_image)
    measurement = f.extract()[name]
    values = measurement.values

    feature_image = create_feature_image(values, labeled_image)
    if not measurement.empty:
        if lower_threshold is None:
            lower_threshold = np.min(values)
        if upper_threshold is None:
            upper_threshold = np.max(values)
        logger.info(
            'keep objects with "%s" values in the range [%d, %d]',
            feature, lower_threshold, upper_threshold
        )

        condition_image = np.logical_or(
            feature_image < lower_threshold, feature_image > upper_threshold
        )
        filtered_image = labeled_image.copy()
        filtered_image[condition_image] = 0
    else:
        logger.warn('no objects detected in image')
        filtered_image = labeled_image
    filtered_mask = filtered_image > 0

    if plot:
        from jtlib import plotting
        plots = [
            plotting.create_mask_image_plot(mask, 'ul'),
            plotting.create_float_image_plot(feature_image, 'ur'),
            plotting.create_mask_image_plot(filtered_mask, 'll'),
        ]
        n_removed = (
            len(np.unique(labeled_image)) - len(np.unique(filtered_image))
        )
        figure = plotting.create_figure(
            plots,
            title='Filtered for feature "{0}": {1} objects removed'.format(
                feature, n_removed
            )
        )
    else:
        figure = str()

    return Output(filtered_mask, figure)
