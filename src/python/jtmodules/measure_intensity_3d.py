import features


def measure_intensity_3d(label_image, intensity_image, plot=False):
    '''
    Jterator module for measuring intensity features for objects defined by
    `label_image` based on greyscale values in `intensity_image`.

    Parameters
    ----------
    label_image: numpy.ndarray[int32]
        labeled image; pixels with the same label encode an object
    intensity_image: numpy.ndarray[unit8 or uint16]
        grayscale image that should be used to measure intensity
    plot: bool, optional
        whether a plot should be generated (default: ``False``)

    Returns
    -------
    Dict[str, pandas.DataFrame[float] or str]
        * "measurements": extracted intensity features
        * "figure": html string in case `plot` is ``True``

    Returns
    -------
    Dict[str, pandas.DataFrame[float] or str]
        * "measurements": extracted intensity features

    See also
    --------
    :py:class:`jtlib.features.Intensity`
    '''
    
    siz = label_image.shape
    output1 = []
    
    if (len(siz) == 2):
        f = features.Intensity(
                label_image=label_image,
                intensity_image=intensity_image
                )

        outputs = {'measurements': f.extract()}
    
    elif (len(siz) > 2):
        
        for i in range(0,siz[2]):

            label_image1 = label_image[:,:,i]
            intensity_image1 = intensity_image[:,:,i]
            
            f = features.Intensity(
                label_image=label_image1,
                intensity_image=intensity_image1
                )
            
            output1.append(f.extract()) 
     
        outputs = {'measurements': output1}      


    if plot:
        outputs['figure'] = f.plot()
    else:
        outputs['figure'] = str()

    return outputs
