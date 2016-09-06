import logging
import numpy as np
import mahotas as mh
from jtlib import utils

logger = logging.getLogger(__name__)

VERSION = '0.0.2'


SUPPORTED_FEATURES = {
    'area': mh.labeled.labeled_size,
    'perimenter': mh.labeled.bwperim,
    'excentricity': mh.features.eccentricity,
    'roundness': mh.features.roundness,
}


def main(input_mask, feature, threshold, remove, plot):
    '''Filters objects (labeled connected components) based on specified
    features.

    Parameters
    ----------
    input_mask: numpy.ndarray[numpy.int32]
        labeled image that should be filtered
    feature: str
        name of the feature based on which the image should be filtered
    threshold:
        threshold level (type depends on the chosen `feature`)
    remove: str
        remove objects ``"below"`` or ``"above"`` `threshold`
    plot: bool, optional
        whether a plot should be generated (default: ``False``)

    Returns
    -------
    Dict[str, numpy.ndarray[int32] or str]
        "filtered_image": filtered label image
        "figure": JSON string figure representation

    Raises
    ------
    TypeError
        when `input_mask` is not binary
    ValueError
        when value of `remove` is not ``"below"`` or ``"above"``
    ValueError
        when value of `feature` is not one of the supported features

    '''
    if input_mask.dtype != np.bool:
        raise TypeError('Argument "input_mask" must be binary.')
    if feature not in SUPPORTED_FEATURES:
        raise ValueError(
            'Argument "feature" must be one of the following: "%s".'
            % '", "'.join(SUPPORTED_FEATURES.keys())
        )

    labeled_image = mh.label(input_mask)[0]
    feature_image = SUPPORTED_FEATURES[feature](labeled_image)
    if remove == 'above':
        logger.info(
            'remove objects with "%s" values above %d', feature, threshold
        )
        condition_image = feature_image > threshold
    elif remove == 'below':
        condition_image = feature_image < threshold
        logger.info(
            'remove objects with "%s" values below %d', feature, threshold
        )
    else:
        raise ValueError(
            'Argument "remove" must be a either "above" or "below".'
        )

    filtered_image = mh.labeled.remove_regions_where(
        labeled_image, condition_image
    )

    n_removed = len(np.unique(labeled_image)) - len(np.unique(filtered_image))

    output_mask = filtered_image > 0
    output = {'output_mask': output_mask}
    if plot:
        from jtlib import plotting
        plots = [
            plotting.create_mask_image_plot(input_mask, 'ul'),
            plotting.create_mask_image_plot(output_mask, 'ur'),
        ]
        output['figure'] = plotting.create_figure(
            plots,
            title='''removed %d objects with %s values %s %d
            ''' % (n_removed, feature, remove, threshold)
        )
    else:
        output['figure'] = str()

    return output
