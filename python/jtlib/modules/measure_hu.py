import jtlib.features


def measure_hu(label_image, intensity_image, objects_name, channel_name,
               plot=False):
    '''
    Jterator module for measuring weighted Hu texture features for objects
    in a labeled image.

    Parameters
    ----------
    label_image: numpy.ndarray[int32]
        labeled image; pixels with the same label encode an object
    intensity_image: numpy.ndarray[unit8 or uint16]
        grayscale input image
    objects_name: str
        name of the objects in `label_image`
    channel_name: str
        name of the channel corresponding to `intensity_image`
    plot: bool, optional
        whether a plot should be generated (default: ``False``)

    Returns
    -------
    Dict[str, pandas.DataFrame[float] or str]
        "measurements": extracted Hu features
        "figure": html string in case ``kwargs["plot"] == True``

    See also
    --------
    :py:class:`jtlib.features.Hu`
    '''
    f = jtlib.features.Hu(
            label_image=label_image,
            intensity_image=intensity_image,
            objects_name=objects_name,
            channel_name=channel_name
    )
    return {'measurements': f.extract()}
