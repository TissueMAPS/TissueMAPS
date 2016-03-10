import jtlib.features


def measure_zernike(label_image, objects_name, plot=False):
    '''
    Jterator module for measuring Zernike features of objects
    (connected components) in a labeled image.
    For more details see
    `mahotas docs <http://mahotas.readthedocs.org/en/latest/features.html>`_.

    Parameters
    ----------
    label_image: numpy.ndarray[int32]
        labeled image; pixels with the same label encode an object
    objects_name: str
        name of the objects in `label_image`
    plot: bool, optional
        whether a plot should be generated (default: ``False``)

    Returns
    -------
    Dict[str, pandas.DataFrame[float] or str]
        "measurements": extracted Zernike features
        "figure": html string in case ``kwargs["plot"] == True``

    See also
    --------
    :py:class:`jtlib.features.Zernike`
    '''
    f = jtlib.features.Zernike(
                    label_image=label_image,
                    objects_name=objects_name
    )
    return {'measurements': f.extract()}
