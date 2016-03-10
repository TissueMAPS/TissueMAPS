import jtlib.features


def measure_haralick(label_image, intensity_image, channel_name, plot=False):
    '''
    Jterator module for measuring Haralick texture features for objects in a
    labeled image.

    Parameters
    ----------
    label_image: numpy.ndarray[int32]
        labeled image; pixels with the same label encode an object
    intensity_image: numpy.ndarray[unit8 or uint16]
        grayscale input image
    channel_name: str
        name of the `intensity_image` channel
    plot: bool, optional
        whether a plot should be generated (default: ``False``)

    Returns
    -------
    Dict[str, pandas.DataFrame[float] or str]
        "measurements": extracted Haralick features
        "figure": html string in case ``kwargs["plot"] == True``

    See also
    --------
    :py:class:`jtlib.features.Haralick`
    '''
    f = jtlib.features.Haralick(
            label_image=label_image,
            channel_name=channel_name,
            intensity_image=intensity_image
    )
    return {'measurements': f.extract()}
