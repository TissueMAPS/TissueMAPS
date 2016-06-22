import logging

logger = logging.getLogger(__name__)

VERSION = '0.0.1'


def main(label_image):
    '''Registeres segmented objects in a labeled image for use by other
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
