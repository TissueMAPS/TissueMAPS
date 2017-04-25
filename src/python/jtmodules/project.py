import numpy as np
import collections
import logging

VERSION = '0.1.0'

Output = collections.namedtuple('Output', ['projected_image', 'figure'])

logger = logging.getLogger(__name__)

projections = {
    'max': np.max,
    'sum': np.sum
}


def main(image, method='max', plot=False):
    '''Projects an image along the last dimension using the given `method`.
    
    Parameters
    ----------
    image: numpy.ndarray[Union[numpy.uint8, numpy.uint16]]
        grayscale image
    method: str, optional
        method used for projection
        (default: ``"max"``, options: ``{"max", "sum"}``)
    plot: bool, optional
        whether a figure should be created (default: ``False``)
    '''
    logger.info('project image using "%s" method', method)
    func = projections[method]
    projected_image = func(image, axis=-1)

    if plot:
        logger.info('create plot')
        from jtlib import plotting
        plots = [
	    plotting.create_intensity_image_plot(
                projected_image, 'ul', clip=True
            )
	]
        figure = plotting.create_figure(plots, title='projected image')
    else:
        figure = str()

    return Output(projected_image, figure)

