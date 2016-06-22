import scipy.ndimage as ndi

VERSION = '0.0.1'

def main(label_image, n, plot=False):
    '''Expands objects in `label_image` by `n` pixels along each axis.

    Parameters
    ----------
    label_image: numpy.ndarray[numpy.int32]
        image where each connected pixel component is labeled with a unique
        non-zero number
    n: int
        number of pixels by which each connected component should be expanded
    plot: bool, optional
        whether a plot should be generated (default: ``False``)

    Returns
    -------
    Dict[str, numpy.ndarray[numpy.int32] or str]
        "expanded_objects": label image with expanded objects
        "figure": html string in case `plot` is ``True``
    '''
    # NOTE: code from CellProfiler module "expandorshrink"
    background = label_image == 0
    distance, (i, j) = distance_transform_edt(background, return_indices=True)
    expanded_image = label_image.copy()
    mask = background & (distance < n)
    expanded_image[mask] = label_image[i[mask], j[mask]]
    output['expanded_image'] = expanded_image
    output['figure'] = str()
    return output
