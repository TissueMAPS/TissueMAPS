import logging
import numpy as np
import mahotas as mh
from skimage.segmentation import clear_border
from skimage.measure import label
from skimage.measure import regionprops
from scipy import ndimage as ndi
import skimage as sk
from skimage.morphology import watershed, binary_dilation
from matplotlib import pyplot as plt

logger = logging.getLogger(__name__)


def main(input_label_image, input_image, background_level, plot=False):
    '''Detects secondary objects in an image by expanding the primary objects
    encoded in `input_label_image`. The outlines of secondary objects are
    determined based on the watershed transform of `input_image` using the
    primary objects in `input_label_image` as seeds.

    Parameters
    ----------
    input_label_image: numpy.ndarray[numpy.int32]
        2D labeled array encoding primary objects, which serve as seeds for
        watershed transform
    input_image: numpy.ndarray[numpy.uint8 or numpy.uint16]
        2D grayscale array that serves as gradient for watershed transform
    background_level: int
        prevents expansion of objects beyond this intensitiy value
    plot: bool, optional
        whether a plot should be generated

    Returns
    -------
    Dict[str, numpy.ndarray[numpy.int32] or str]
        * "output_label_image": 2D labeled array of secondary objects
        * "figure": JSON figure representation

    '''
    if np.any(input_label_image == 0):
        has_background = True
    else:
        has_background = False

    if not has_background:
        output_label_image = input_label_image
    else:
        logger.info('detect secondary objects via watershed transform')
        regions = mh.cwatershed(np.invert(input_image), input_label_image)
        # Ensure objects are separated
        lines = mh.labeled.borders(regions)
        regions[lines] = 0
        # Remove "background" regions
        logger.info(
            'remove background regions with values below %d', background_level
        )
        background_mask = input_image < background_level
        regions[background_mask] = 0
        # Remove objects that are obviously too small
        min_size = np.min(mh.labeled.labeled_size(input_label_image))
        sizes = mh.labeled.labeled_size(regions)
        too_small = np.where(sizes < min_size)
        regions = mh.labeled.remove_regions(regions, too_small)

        # Remove regions that don't overlap with primary objects and assign
        # correct labels, i.e. those of the secondary objects
        logger.info('relabel secondary objects according to primary objects')
        se = np.ones((3, 3), bool)  # use 8-connected neighbourhood
        new_label_image, n_new_labels = mh.label(regions > 0, Bc=se)
        lut = np.zeros(np.max(new_label_image)+1, new_label_image.dtype)
        for i in range(1, n_new_labels+1):
            orig_labels = input_label_image[new_label_image == i]
            orig_labels = orig_labels[orig_labels > 0]
            orig_count = np.bincount(orig_labels)
            orig_unique = np.where(orig_count)[0]
            if orig_unique.size == 1:
                lut[i] = orig_unique[0]
            elif orig_unique.size > 1:
                logger.debug(
                    'overlapping objects: %s',
                    ', '.join(map(str, orig_unique))
                )
                lut[i] = np.where(orig_count == np.max(orig_count))[0][0]
        output_label_image = lut[new_label_image]

    output = dict()
    output['output_label_image'] = output_label_image

    if plot:
        from jtlib import plotting
        n_objects = len(np.unique(output_label_image)[1:])
        colorscale = plotting.create_colorscale(
            'Spectral', n=n_objects, permute=True, add_background=True
        )
        plots = [
            plotting.create_mask_image_plot(
                input_label_image, 'ul', colorscale=colorscale
                ),
            plotting.create_mask_image_plot(
                output_label_image, 'ur', colorscale=colorscale
            ),
            plotting.create_overlay_image_plot(
                input_image, output_label_image, 'll'
            )
        ]
        output['figure'] = plotting.create_figure(
            plots, title='secondary objects'
        )
    else:
        output['figure'] = str()

    return output

