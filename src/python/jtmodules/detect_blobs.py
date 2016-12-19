'''Jterator module for detection of blobs in images.'''
import sep
import numpy as np
import mahotas as mh
import collections
import logging


logger = logging.getLogger(__name__)

sep.set_extract_pixstack(10**6)

Output = collections.namedtuple('Output', ['mask', 'figure'])


def main(image, threshold_factor, plot=False):
    '''Detects blobs in `image` using a Python implementation of
    `SExtractor <http://www.astromatic.net/software/sextractor>`_ [1].

    Parameters
    ----------
    image: numpy.ndarray[numpy.uint8 or numpy.uint16]
        image in which blobs should be detected
    thresh: int
        factor by which pixel values must be above background RMS noise
        to be considered part of a blob
    plot: bool, optional
        whether a plot should be generated (default: ``False``)

    Returns
    -------
    jtmodules.detect_blobs.Output

    References
    ----------
    _[1] Bertin, E. & Arnouts, S. 1996: SExtractor: Software for source extraction, Astronomy & Astrophysics Supplement 317, 393
    '''

    img = image.astype('float')

    logger.info('estimate background')
    bkg = sep.Background(img)

    logger.info('subtract background')
    img_sub = img - bkg

    logger.info('detect blobs')
    out, label_image = sep.extract(
        img_sub, threshold_factor, err=bkg.globalrms, segmentation_map=True
    )
    mask = np.zeros(img.shape, dtype=bool)
    mask[out['y'].astype(int), out['x'].astype(int)] = True

    if plot:
        logger.info('create plot')
        from jtlib import plotting
        outlines = mh.morph.dilate(mh.labeled.bwperim(label_image))
        plots = [
            plotting.create_intensity_overlay_image_plot(
                image, outlines, 'ul', clip=True
            ),
            plotting.create_mask_image_plot(label_image, 'ur')
        ]
        figure = plotting.create_figure(plots, title='detected blobs')
    else:
        figure = str()

    return Output(mask, figure)
