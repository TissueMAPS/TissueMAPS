from skimage import measure
from skimage import filters
from jtlib import utils
from jtlib import features
from tmlib.writers import DatasetWriter


def measure_texture(labeled_image, objects_name, intensity_image, layer_name,
                    hu=False, haralick=False, tas=False, gabor=False, surf=False,
                    **kwargs):
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
        whether Hu moments should be measured (default: ``False``)
    haralick: bool, optional
        whether Haralick features should be measured (default: ``False``)
    tas: bool, optional
        whether Threshold Adjancency Statistics (TAS) should be measured
        (default: ``False``)
    gabor: bool, optional
        whether Gabor texture features should be measured
    surf: bool, optional
        whether Speeded-Up Robust Features should be measured
    **kwargs: dict
        additional arguments provided by Jterator:
        "data_file", "figure_file", "experiment_dir", "plot", "job_id"

    See also
    --------
    `jtlib.features`
    '''
    measurements = dict()
    if hu:
        measurements['hu'] = list()
    if haralick:
        measurements['haralick'] = list()
    if tas:
        measurements['tas'] = list()
    if gabor:
        measurements['gabor'] = list()
    if surf:
        measurements['surf'] = list()

    if labeled_image.shape != intensity_image.shape:
        raise Exception('Size of intensity and object image must be identical')

    # Get coordinates of region containing individual objects
    regions = measure.regionprops(
                labeled_image, intensity_image=intensity_image)

    # Calculate threshold across the whole image
    threshold = filters.threshold_otsu(intensity_image)

    for j, r in enumerate(regions):

        # Extract region of current object
        mask = utils.crop_image(labeled_image, bbox=r.bbox)
        mask = mask == (j+1)  # only current object

        img = utils.crop_image(intensity_image, bbox=r.bbox)

        # Weighted hu moments
        if 'hu' in measurements:
            feats = features.measure_hu(r)
            measurements['hu'].append(feats)

        # Haralick texture features
        if 'haralick' in measurements:
            feats = features.measure_haralick(img, mask)
            measurements['haralick'].append(feats)

        # Threshold Adjacency Statistics
        if 'tas' in measurements:
            feats = features.measure_tas(img, mask, threshold=threshold)
            measurements['tas'].append(feats)

        # Gabour filters
        if 'gabor' in measurements:
            feats = features.measure_gabor(img, mask)
            measurements['gabor'].append(feats)

        # Speeded-Up Robust Features
        if 'surf' in measurements:
            feats = features.measure_surf(img, mask)
            measurements['surf'].append(feats)

    with DatasetWriter(kwargs['data_file']) as data:
        for m in measurements:
            if len(measurements[m]) == 0:
                data.create_group('objects/%s/features' % objects_name)
                continue
            feature_names = measurements[m][0].keys()
            for f in feature_names:
                feats = [item[f] for item in measurements[m]]
                data.write('/objects/%s/features/Texture_%s_%s'
                           % (objects_name, layer_name, f),
                           data=feats)
