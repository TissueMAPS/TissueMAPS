from skimage import measure
from skimage import filters
from jtlib import utils
from jtlib import features
from tmlib.writers import DatasetWriter


def measure_texture(labeled_image, objects_name, intensity_image, layer_name,
                    hu=False, haralick=False, tas=False, **kwargs):
    '''
    Jterator module for measuring texture features in an image.
    For more details see
    `mahotas docs <http://mahotas.readthedocs.org/en/latest/features.html>`_.

    Parameters
    ----------
    labeled_image: numpy.ndarray[int]
        labeled input image
    objects_name: str
        name of the objects (labeled connected components) in `labeled_image`
    intensity_image: numpy.ndarray
        grayscale input image
    layer_name: str
        name of the `intensity_image` channel
    hu: bool, optional
        whether Hu moments should be measured (defaults to False)
    haralick: bool, optional
        whether Haralick features should be measured (defaults to False)
    tas: bool, optional
        whether Threshold Adjancency Statistics (TAS) should be measured
        (defaults to False)
    **kwargs: dict
        additional arguments provided by Jterator:
        "data_file", "figure_file", "experiment_dir", "plot", "job_id"

    See also
    --------
    `jtlib.features`
    '''
    measurement_names = []
    if hu:
        measurement_names.append('hu')
    if haralick:
        measurement_names.append('haralick')
    if tas:
        measurement_names.append('tas')

    if labeled_image.shape != intensity_image.shape:
        raise Exception('Size of intensity and object image must be identical')

    # Get coordinates of region containing individual objects
    regions = measure.regionprops(
                labeled_image, intensity_image=intensity_image)

    # Calculate threshold across the whole image
    threshold = filters.threshold_otsu(intensity_image)
    BINS = 32

    data = dict()
    measurements = dict()
    for m in measurement_names:
        measurements[m] = list()
    for j, r in enumerate(regions):

        # Crop images to region of current object
        mask = utils.crop_image(labeled_image, bbox=r.bbox)
        mask = mask == (j+1)  # only current object

        tas = utils.crop_image(intensity_image, bbox=r.bbox)
        tas[~mask] = 0

        # Weighted hu moments
        if 'hu' in measurement_names:
            feats = features.measure_hu(r)
            measurements['hu'].append(feats)

        # haralick texture features
        if 'haralick' in measurement_names:
            feats = features.measure_haralick(tas, bins=BINS)
            measurements['haralick'].append(feats)

        # Threshold Adjacency Statistics
        if 'tas' in measurement_names:
            feats = features.measure_tas(tas, threshold=threshold)
            measurements['tas'].append(feats)

        # TODO: Gabour filters

    for m in measurement_names:
        feature_names = measurements[m][0].keys()
        for f in feature_names:
            feats = [item[f] for item in measurements[m]]
            data['Texture_%s_%s' % layer_name, f] = feats

    with DatasetWriter(kwargs['data_file']) as f:
        for k, v in data.iteritems():
            f.write('%s/features/%s' % (objects_name, k), data=v)
