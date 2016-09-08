import logging
import numpy as np
import mahotas as mh
from jtlib import utils

logger = logging.getLogger(__name__)

VERSION = '0.0.3'


SUPPORTED_FEATURES = {
    'area': mh.labeled.labeled_size,
    'perimenter': mh.labeled.bwperim,
    'excentricity': mh.features.eccentricity,
    'roundness': mh.features.roundness,
}


def main(input_mask, feature, lower_threshold=None, upper_threshold=None,
        plot=False):
    '''Filters objects (labeled connected components) based on specified
    value range for a given `feature`.

    Parameters
    ----------
    input_mask: numpy.ndarray[numpy.bool]
        binary image that should be filtered
    feature: str
        name of the feature based on which the image should be filtered
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
    Dict[str, numpy.ndarray[int32] or str]
        "output_mask": filtered image
        "figure": JSON string figure representation

    Raises
    ------
    TypeError
        when `input_mask` is not binary
    ValueError
        when both `lower_threshold` and `upper_threshold` are ``None``
    ValueError
        when value of `feature` is not one of the supported features

    '''
    if input_mask.dtype != np.bool:
        raise TypeError('Argument "input_mask" must be binary.')
    if lower_threshold is None and upper_threshold is None:
        raise ValueError(
            'Arugment "lower_threshold" or "upper_threshold" must be provided. '
        )
    if feature not in SUPPORTED_FEATURES:
        raise ValueError(
            'Argument "feature" must be one of the following: "%s".'
            % '", "'.join(SUPPORTED_FEATURES.keys())
        )

    labeled_image = mh.label(input_mask)[0]
    feature_image = SUPPORTED_FEATURES[feature](labeled_image)
    if lower_threshold is None:
        lower_threshold = np.min(feature_image.flat)
    if upper_threshold is None:
        upper_threshold = np.max(feature_image.flat)
    logger.info(
        'keep objects with "%s" values in the range [%d, %d]',
        feature, lower_threshold, upper_threshold
    )

    condition_image = np.logical_and(
        feature_image < lower_threshold, feature_image > upper_threshold
    )
    filtered_image = mh.labeled.remove_regions_where(
        labeled_image, condition_image
    )
    output_mask = filtered_image > 0

    output = {'output_mask': output_mask}
    if plot:
        from jtlib import plotting
        plots = [
            plotting.create_mask_image_plot(input_mask, 'ul'),
            plotting.create_mask_image_plot(output_mask, 'ur'),
        ]
        n_removed = len(np.unique(labeled_image)) - len(np.unique(filtered_image))
        output['figure'] = plotting.create_figure(
            plots,
            title='''removed %d objects with "%s" values outside of [%d, %d]
            ''' % (n_removed, feature, lower_threshold, upper_threshold)
        )
    else:
        output['figure'] = str()

    return output
