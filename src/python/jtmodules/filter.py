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

logger = logging.getLogger(__name__)

VERSION = '0.0.3'

SUPPORTED_FEATURES = {
    'area': mh.labeled.labeled_size,
    'perimenter': mh.labeled.bwperim,
    'eccentricity': mh.features.eccentricity,
    'roundness': mh.features.roundness,
}

Output = collections.namedtuple('Output', ['filtered_mask', 'figure'])


def main(mask, feature, lower_threshold=None, upper_threshold=None,
        plot=False):
    '''Filters objects (labeled connected components) based on the specified
    value range for a given `feature`.

    Parameters
    ----------
    mask: numpy.ndarray[numpy.bool]
        binary image that should be filtered
    feature: str
        name of the feature based on which the image should be filtered
        (options: ``{"area", "perimeter", "eccentricity", "roundness"}``)
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
    TypeError
        when `mask` is not binary
    ValueError
        when both `lower_threshold` and `upper_threshold` are ``None``
    ValueError
        when value of `feature` is not one of the supported features

    '''
    if mask.dtype != np.bool:
        raise TypeError('Argument "mask" must be binary.')
    if lower_threshold is None and upper_threshold is None:
        raise ValueError(
            'Arugment "lower_threshold" or "upper_threshold" must be provided. '
        )
    if feature not in SUPPORTED_FEATURES:
        raise ValueError(
            'Argument "feature" must be one of the following: "%s".'
            % '", "'.join(SUPPORTED_FEATURES.keys())
        )

    labeled_image = mh.label(mask)[0]
    feature_values = SUPPORTED_FEATURES[feature](labeled_image)
    feature_image = feature_values[labeled_image]
    if lower_threshold is None:
        lower_threshold = np.min(feature_values)
    if upper_threshold is None:
        upper_threshold = np.max(feature_values)
    logger.info(
        'keep objects with "%s" values in the range [%d, %d]',
        feature, lower_threshold, upper_threshold
    )

    condition_image = np.logical_or(
        feature_image < lower_threshold, feature_image > upper_threshold
    )
    filtered_image = labeled_image.copy()
    filtered_image[condition_image] = 0
    filtered_mask = filtered_image > 0

    if plot:
        from jtlib import plotting
        plots = [
            plotting.create_mask_image_plot(mask, 'ul'),
            plotting.create_mask_image_plot(filtered_mask, 'ur'),
        ]
        n_removed = (
            len(np.unique(labeled_image)) - len(np.unique(filtered_image))
        )
        figure = plotting.create_figure(
            plots,
            title='Filtered mask with %d objects removed' % n_removed
        )
    else:
        figure = str()

    return Output(filtered_mask, figure)
