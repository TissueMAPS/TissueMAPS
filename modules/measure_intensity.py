from skimage import measure
from skimage import filters
import jtapi
from jtlib import utils
from jtlib import features


def measure_intensity(ObjectsImage, ObjectsName, ChannelImage, ChannelName,
                      Hu=False, Haralick=False, TAS=False, **kwargs):
    '''
    Jterator module for measuring intensity and texture features in an image.
    For more details see
    `mahotas docs <http://mahotas.readthedocs.org/en/latest/features.html>`_.

    Parameters
    ----------
    ObjectsImage: numpy.ndarray[int]
        labeled input image
    ObjectsName: str
        name of the objects (labeled connected components) in `ObjectsImage`
    ChannelImage: numpy.ndarray
        grayscale input image
    ChannelName: str
        name of the `ChannelImage` channel
    Hu: bool, optional
        whether Hu moments should be measured (defaults to False)
    Haralick: bool, optional
        whether Haralick features should be measured (defaults to False)
    TAS: bool, optional
        whether Threshold Adjancency Statistics should be measured
        (defaults to False)
    **kwargs: dict
        additional arguments provided by Jterator:
        "ProjectDir", "DataFile", "FigureFile", "Plot"

    See also
    --------
    `jtlib.features`
    '''
    measurement_names = []
    measurement_names.append('intensity')  # measured by default
    if Hu:
        measurement_names.append('hu')
    if Haralick:
        measurement_names.append('haralick')
    if TAS:
        measurement_names.append('tas')

    data = dict()

    if ObjectsImage.shape != IntensityInputImage.shape:
        raise Exception('Size of intensity and object image must be identical')

    # Get coordinates of region containing individual objects
    regions = measure.regionprops(ObjectsImage, intensity_image=IntensityInputImage)

    # Calculate threshold across the whole image
    THRESHOLD = filters.threshold_otsu(IntensityInputImage)
    BINS = 32

    measurements = dict()
    for m in measurement_names:
        measurements[m] = list()
    for j, r in enumerate(regions):

        # Crop images to region of current object
        mask = utils.crop_image(ObjectsImage, bbox=r.bbox)
        mask = mask == (j+1)  # only current object

        img = utils.crop_image(IntensityInputImage, bbox=r.bbox)
        img[~mask] = 0
        # plt.imshow(img)
        # plt.show()

        # Intensity
        feats = features.measure_intensity(r, img)
        measurements['intensity'].append(feats)

        # Weighted hu moments
        if 'hu' in measurement_names:
            feats = features.measure_hu(r)
            measurements['hu'].append(feats)

        # Haralick texture features
        if 'haralick' in measurement_names:
            feats = features.measure_haralick(img, bins=BINS)
            measurements['haralick'].append(feats)

        # Threshold Adjacency Statistics
        if 'tas' in measurement_names:
            feats = features.measure_tas(img, threshold=THRESHOLD)
            measurements['tas'].append(feats)

    for m in measurement_names:
        feature_names = measurements[m][0].keys()
        for f in feature_names:
            feats = [item[f] for item in measurements[m]]
            data['%s_Texture_%s_%s' % (ObjectsName, ChannelName, f)] = feats

    jtapi.writedata(data, kwargs['DataFile'])
