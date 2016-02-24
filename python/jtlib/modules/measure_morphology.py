import jtlib.features


def measure_morphology(labeled_image, objects_name, zernike=False, **kwargs):
    '''
    Jterator module for measuring morhological features of objects
    (connected components) in a labeled image.
    For more details see
    `mahotas docs <http://mahotas.readthedocs.org/en/latest/features.html>`_.

    Parameters
    ----------
    labeled_image: numpy.ndarray[int]
        input label image
    objects_name: str
        name of the objects (labeled connected components) in `labeled_image`
    zernike: bool, optional
        whether Zernike moments should be measured (default: ``False``)
    **kwargs: dict
        additional arguments provided by Jterator:
        "data_file", "figure_file", "experiment_dir", "plot", "job_id"

    See also
    --------
    :py:class:`jtlib.features.Morphology`
    :py:class:`jtlib.features.Zernike`
    '''
    m = jtlib.features.Morphology(
                object_name=objects_name,
                label_image=labeled_image,
    )
    morphology_features = m.extract()
    m.save(morphology_features, kwargs['data_file'])

    if zernike:
        z = jtlib.features.Zernike(
                object_name=objects_name,
                label_image=labeled_image,
        )
        morphology_features = z.extract()
        z.save(morphology_features, kwargs['data_file'])
