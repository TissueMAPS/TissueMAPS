import scipy.ndimage as ndi
import collections

VERSION = '0.0.1'

Output = collections.namedtuple('Output', ['expanded_label_image', 'figure'])


def main(label_image, n, plot=False):
    '''Expands objects in `label_image` by `n` pixels along each axis.

    Parameters
    ----------
    label_image: numpy.ndarray[numpy.int32]
        2D label image with objects that should be expanded
    n: int
        number of pixels by which each connected component should be expanded
    plot: bool, optional
        whether a plot should be generated (default: ``False``)

    Returns
    -------
    jtmodules.expand_objects.Output
    '''
    # NOTE: code from CellProfiler module "expandorshrink"
    background = label_image == 0
    distance, (i, j) = distance_transform_edt(background, return_indices=True)
    expanded_image = label_image.copy()
    mask = background & (distance < n)
    expanded_image[mask] = label_image[i[mask], j[mask]]

    if plot:
        # TODO
        figure = str()
    else:
        figure = str()

    return Output(expanded_image, figure)
