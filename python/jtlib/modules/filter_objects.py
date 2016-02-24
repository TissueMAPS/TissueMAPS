import skimage.measure
import collections
import numpy as np
from .. import utils


def filter_objects(labeled_image, feature, threshold, keep, relabel, **kwargs):
    '''
    Jterator module to filter labeled image regions (objects) based
    on measured features.

    Parameters
    ----------
    labeled_image: numpy.ndarray[int]
        labeled image that should be filtered
    feature: str
        name of the region property based on which the image should be filtered
        see `scikit-image docs <http://scikit-image.org/docs/dev/api/skimage.measure.html#regionprops>`_
    threshold:
        threshold level (type depends on the chosen `feature`)
    keep: str
        ``"below"`` or ``"above"``
    relabel: bool
        relabel objects after filtering
    **kwargs: dict
        additional arguments provided by Jterator:
        "data_file", "figure_file", "experiment_dir", "plot", "job_id"

    Returns
    -------
    collections.namedtuple[numpy.ndarray[bool]]
        filtered label image: "filtered_objects"

    Raises
    ------
    ValueError
        when value of `keep` is incorrect
    '''
    regions = skimage.measure.regionprops(labeled_image)
    if keep == 'above':
        ids_to_keep = [r['label'] for r in regions if r[feature] > threshold]
    elif keep == 'below':
        ids_to_keep = [r['label'] for r in regions if r[feature] < threshold]
    else:
        raise ValueError('Value of argument `keep` must be a either '
                         '"above" or "below"')

    filtered_image = np.zeros(labeled_image.shape)
    for ix in ids_to_keep:
        filtered_image[labeled_image == ix] = ix

    if relabel:
        filtered_image = utils.label_image(filtered_image > 0)

    if kwargs['plot']:
        import matplotlib.pyplot as plt
        from .. import plotting

        fig = plt.figure()
        ax1 = fig.add_subplot(1, 2, 1)
        ax2 = fig.add_subplot(1, 2, 2)

        img_obj = labeled_image.copy().astype(float)
        img_obj[labeled_image == 0] = np.nan

        ax1.imshow(img_obj, cmap=plt.cm.jet, interpolation='none')
        ax1.set_title('input objects', size=20)

        img_obj = filtered_image.copy().astype(float)
        img_obj[filtered_image == 0] = np.nan

        ax2.imshow(img_obj, cmap=plt.cm.jet, interpolation='none')
        ax2.set_title('filtered objects', size=20)

        fig.tight_layout()

        plotting.save_mpl_figure(fig, kwargs['figure_file'])

    Output = collections.namedtuple('Output', 'filtered_objects')
    return Output(filtered_image)
