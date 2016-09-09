'''Jterator module for measuring Haralick texture features.'''
import collections
import jtlib.features

VERSION = '0.0.1'

Output = collections.namedtuple('Output', ['measurements', 'figure'])


def main(label_image, intensity_image, plot=False):
    '''Measures texture features for objects in `label_image` based on
    grayscale values in `intensity_image`.

    Parameters
    ----------
    label_image: numpy.ndarray[int32]
        label image with objects that should be measured
    intensity_image: numpy.ndarray[unit8 or uint16]
        grayscale image
    plot: bool, optional
        whether a plot should be generated (default: ``False``)

    Returns
    -------
    jtmodules.maeasure_gabor.Output

    See also
    --------
    :py:class:`jtlib.features.Haralick`
    '''
    f = jtlib.features.Haralick(
            label_image=label_image,
            intensity_image=intensity_image
    )

    measurements = [f.extract()]

    if plot:
        figure = f.plot()
    else:
        figure = str()

    return Output(measurements, figure)
