import logging

logger = logging.getLogger(__name__)


def register_objects(label_image):
    '''
    Jterator module for registering segmented objects for use by other
    (measurement) modules downstream in the pipeline.

    Parameters
    ----------
    label_image: numpy.ndarray[int32]
        labeled image where pixel values encode objects IDs

    Returns
    -------
    Dict[str, numpy.ndarray[int32]]
        * "objects": label_image
    '''
    return {'objects': label_image}
