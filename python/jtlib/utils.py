import numpy as np
import mahotas as mh
from skimage import measure, morphology


def create_outline_image(im):
    '''
    Create an image representing the outlines of objects (connected components)
    in a binary mask image.

    Parameters
    ----------
    im: numpy.ndarray
        binary image

    Returns
    -------
    numpy.ndarray
        outlines of the objects in `im`
    '''
    eroded_image = morphology.binary_erosion(im > 0)
    contours = measure.find_contours(eroded_image, False)
    contours = np.concatenate(contours).astype(int)

    outlines = np.zeros(im.shape)
    outlines[contours[:, 0], contours[:, 1]] = 1

    return outlines


def crop_image(im, bbox, pad=False):
    '''
    Crop image according to bounding box coordinates.

    Parameters
    ----------
    im: numpy.ndarray
        image
    bbox: List[int]
        bounding box coordinates
    pad: bool, optional
        pad cropped image with one line of zero values along each dimension
        (default: ``False``)

    Returns
    -------
    numpy.ndarray
        cropped image
    '''
    im = im[bbox[0]:bbox[2], bbox[1]:bbox[3]]
    if pad:
        im = np.lib.pad(im, (1, 1), 'constant', constant_values=(0))
    return im


def get_border_ids(im):
    '''
    Get the ids of objects that lie at the border of an image.

    Parameters
    ----------
    im: numpy.ndarray[numpy.int32]
        labeled image

    Returns
    -------
    List[int]
        object ids
    '''
    borders = [
        np.unique(im[0, :]),
        np.unique(im[-1, :]),
        np.unique(im[:, 0]),
        np.unique(im[:, -1])
    ]
    border_ids = list(reduce(set.union, map(set, borders)).difference({0}))
    object_ids = np.unique(im[im != 0])
    return [i for i in object_ids if i in border_ids]


def label_image(im):
    '''
    Label connected components in an image with a unique value.
    For more information see
    `mahotas docs <http://mahotas.readthedocs.org/en/latest/labeled.html#labeling-images>`_.

    Parameters
    ----------
    im: numpy.ndarray[bool or int]
        binary image that should be labeled

    Returns
    -------
    numpy.ndarray[int]
        labeled image

    Raises
    ------
    TypeError
        when `im` is not binary
    '''
    if not(all([e in {False, True, 0, 1} for e in np.unique(im)])):
        raise TypeError('Image must be binary')
    labeled_image, n_objects = mh.label(im)
    return labeled_image


def downsample_image(im, bins):
    '''
    Murphy et al. 2002
    "Robust Numerical Features for Description and Classification of
    Subcellular Location Patterns in Fluorescence Microscope Images"

    Parameters
    ----------
    im: numpy.ndarray
        grayscale image
    bins: int
        number of bins

    Returns
    -------
    numpy.ndarray
        downsampled image
    '''
    if bins != 256:
        min_val = im.min()
        max_val = im.max()
        ptp = max_val - min_val
        if ptp:
            return np.array((im-min_val).astype(float) * bins/ptp,
                            dtype=np.uint8)
        else:
            return np.array(im.astype(float), dtype=np.uint8)
