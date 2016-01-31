from jtlib.features import Hu
from jtlib.features import TAS
from jtlib.features import Gabor
from jtlib.features import Haralick


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
    # Weighted hu moments
    if hu:
        f_hu = Hu(
                object_name=objects_name,
                label_image=labeled_image,
                channel_name=layer_name,
                intensity_image=intensity_image
        )
        features = f_hu.extract()
        f_hu.save(features, kwargs['data_file'])

    # Haralick texture features
    if haralick:
        f_haralick = Haralick(
                object_name=objects_name,
                label_image=labeled_image,
                channel_name=layer_name,
                intensity_image=intensity_image
        )
        features = f_haralick.extract()
        f_haralick.save(features, kwargs['data_file'])

    # Threshold Adjacency Statistics
    if tas:
        f_tas = TAS(
                object_name=objects_name,
                label_image=labeled_image,
                channel_name=layer_name,
                intensity_image=intensity_image
        )
        features = f_tas.extract()
        f_tas.save(features, kwargs['data_file'])

    # Gabour filters
    if gabor:
        f_gabor = Gabor(
                object_name=objects_name,
                label_image=labeled_image,
                channel_name=layer_name,
                intensity_image=intensity_image
        )
        features = f_gabor.extract()
        f_gabor.save(features, kwargs['data_file'])

    # TODO: Speeded-Up Robust Features
