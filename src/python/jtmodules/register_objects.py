import logging

logger = logging.getLogger(__name__)

VERSION = '0.0.1'


def main(label_image, as_polygon=True):
    '''Registeres segmented objects in a labeled image for use by other
    (measurement) modules downstream in the pipeline.

    Parameters
    ----------
    label_image: numpy.ndarray[int32]
        labeled image where pixel values encode objects IDs
    as_polygon: boolean, optional
        whether objects should be represented as polygons;
        if ``False`` they will be represented as lines (default: ``True``)

    Returns
    -------
    Dict[str, numpy.ndarray[int32]]
        * "objects": label_image
    '''
    return {
        'objects': label_image,
        'as_polygons': as_polygons 
    }
