from skimage import measure
import collections
import pylab as plt
from tmlib.jterator import jtapi
from jtlib import utils


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
    namedtuple[numpy.ndarray[bool]]
        filtered label image: "filtered_objects"

    Raises
    ------
    ValueError
        when value of `keep` is incorrect
    '''
    # if not isinstance(labeled_image, np.uint):
    #     raise TypeError('"labeled_image" must have unsigned integer type')
    regions = measure.regionprops(labeled_image)
    if keep == 'above':
        ids_to_remove = [r['label'] for r in regions if r[feature] < threshold]
    elif keep == 'below':
        ids_to_remove = [r['label'] for r in regions if r[feature] > threshold]
    else:
        raise ValueError('Value of argument `keep` must be a either '
                         '"above" or "below"')

    filtered_image = labeled_image.copy()
    for ix in ids_to_remove:
        filtered_image[labeled_image == ix] = 0

    if relabel:
        filtered_image = utils.label_image(filtered_image > 0)

    if kwargs['plot']:

        fig = plt.figure(figsize=(10, 10))
        ax1 = fig.add_subplot(1, 2, 1)
        ax2 = fig.add_subplot(1, 2, 2)

        ax1.imshow(labeled_image)
        ax1.set_title('input objects', size=20)

        ax2.imshow(filtered_image)
        ax2.set_title('filtered objects', size=20)

        fig.tight_layout()

        jtapi.savefigure(fig, kwargs['figure_file'])

    output = collections.namedtuple('Output', 'filtered_objects')
    return output(filtered_image)
