from jtlib.features import Intensity


def measure_intensity(labeled_image, objects_name, intensity_image, layer_name,
                      **kwargs):
    '''
    Jterator module for measuring intensity features for objects defined by
    `labeled_image` based on greyscale values in `intensity_image`.

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
    :py:class:`jtlib.features.Intensity`
    '''
    f = Intensity(
                object_name=objects_name,
                label_image=labeled_image,
                channel_name=layer_name,
                intensity_image=intensity_image
    )
    features = f.extract()
    f.save(features, kwargs['data_file'])
