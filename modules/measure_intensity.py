from skimage import measure
from jtlib import utils
from jtlib import features
from tmlib.writers import DatasetWriter


def measure_intensity(labeled_image, objects_name, intensity_image, layer_name,
                      **kwargs):
    '''
    Jterator module for measuring intensity features for objects defined by
    `labeled_image` based on greyscale values in `intensity_image`.
    For more details see
    `scikit-image docs <http://scikit-image.org/docs/dev/api/skimage.measure.html?highlight=regionprops#skimage.measure.regionprops>`_.

    Parameters
    ----------
    labeled_image: numpy.ndarray[int]
        labeled image
    objects_name: str
        name of the objects in `labeled_image`
    intensity_image: numpy.ndarray[uint]
        grayscale image that should be used to measure intensity
    layer_name: str
        name of the `intensity_image`
    **kwargs: dict
        additional arguments provided by Jterator:
        "data_file", "figure_file", "experiment_dir", "plot", "job_id"

    See also
    --------
    `jtlib.features`

    Raises
    ------
    ValueError
        when `labeled_image` and `intensity_image` have different dimensions
    TypeError
        when `intensity_image` doesn't have unsigned integer type
    '''
    if not str(intensity_image.dtype).startswith('uint'):
        raise TypeError('"intensity_image" must have unsigned integer type')

    if labeled_image.shape != intensity_image.shape:
        raise ValueError(
            'Size of "labeled_image" and "intensity_image" must be identical')

    # Get coordinates of region containing individual objects
    regions = measure.regionprops(labeled_image,
                                  intensity_image=intensity_image)

    measurements = list()
    for j, r in enumerate(regions):

        # Crop images to region of current object
        mask = utils.crop_image(labeled_image, bbox=r.bbox, pad=True)
        mask = mask == (j+1)

        img = utils.crop_image(intensity_image, bbox=r.bbox, pad=True)

        # Intensity
        feats = features.measure_intensity(img, mask, r)
        measurements.append(feats)

    if not len(measurements) == 0:
        feature_names = measurements[0].keys()
        with DatasetWriter(kwargs['data_file']) as data:
            for f in feature_names:
                feats = [item[f] for item in measurements]
                data.write('/objects/%s/features/Intensity_%s_%s'
                           % (objects_name, layer_name, f),
                           data=feats)
