import jtlib.features


def measure_intensity(label_image, intensity_image, objects_name, channel_name,
                      plot=False):
    '''
    Jterator module for measuring intensity features for objects defined by
    `label_image` based on greyscale values in `intensity_image`.

    Parameters
    ----------
    label_image: numpy.ndarray[int32]
        labeled image; pixels with the same label encode an object
    intensity_image: numpy.ndarray[unit8 or uint16]
        grayscale image that should be used to measure intensity
    objects_name: str
        name of the objects in `label_image`
    channel_name: str
        name of the channel corresponding to `intensity_image`
    plot: bool, optional
        whether a plot should be generated (default: ``False``)

    Returns
    -------
    Dict[str, pandas.DataFrame[float] or str]
        "measurements": extracted intensity features
        "figure": html string in case ``kwargs["plot"] == True``

    Returns
    -------
    dict
        outputs as key-value pairs:
            * "objects" (pandas.DataFrame): name of the measured objects

    See also
    --------
    :py:class:`jtlib.features.Intensity`
    '''
    f = jtlib.features.Intensity(
                label_image=label_image,
                intensity_image=intensity_image,
                objects_name=objects_name,
                channel_name=channel_name,
    )
    return {'objects': f.extract()}
