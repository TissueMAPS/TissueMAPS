from skimage import measure
from skimage import filters
import jtapi
from jtlib import utils
from jtlib import features


def measure_texture(objects_image, objects_name, channel_image, channel_name,
                    hu=False, haralick=False, tas=False, **kwargs):
    '''
    Jterator module for measuring texture features in an image.
    For more details see
    `mahotas docs <http://mahotas.readthedocs.org/en/latest/features.html>`_.

    Parameters
    ----------
    objects_image: numpy.ndarray[int]
        labeled input image
    objects_name: str
        name of the objects (labeled connected components) in `objects_image`
    channel_image: numpy.ndarray
        grayscale input image
    channel_name: str
        name of the `channel_image` channel
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

    if objects_image.shape != channel_image.shape:
        raise Exception('Size of intensity and object image must be identical')

    # Get coordinates of region containing individual objects
    regions = measure.regionprops(objects_image, intensity_image=channel_image)

    # Calculate threshold across the whole image
    THRESHOLD = filters.threshold_otsu(channel_image)
    BINS = 32

    data = dict()
    measurements = dict()
    for m in measurement_names:
        measurements[m] = list()
    for j, r in enumerate(regions):

        # Crop images to region of current object
        mask = utils.crop_image(objects_image, bbox=r.bbox)
        mask = mask == (j+1)  # only current object

        tas = utils.crop_image(channel_image, bbox=r.bbox)
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
            feats = features.measure_tas(tas, threshold=THRESHOLD)
            measurements['tas'].append(feats)

    for m in measurement_names:
        feature_names = measurements[m][0].keys()
        for f in feature_names:
            feats = [item[f] for item in measurements[m]]
            data['%s_Texture_%s_%s' % (objects_name, channel_name, f)] = feats

    jtapi.writedata(data, kwargs['data_file'])
