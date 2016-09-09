'''Jterator module for measuring intensity statistics.'''
import collections
import jtlib.features

VERSION = '0.0.1'

Output = collections.namedtuple('Output', ['measurements', 'figure'])


def main(label_image, intensity_image, plot=False):
    '''Measures intensity features for objects in `label_image` based
    on grayscale values in `intensity_image`.

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
    jtmodules.measure_intensity.Output

    See also
    --------
    :py:class:`jtlib.features.Intensity`
    '''
    f = jtlib.features.Intensity(
        label_image=label_image, intensity_image=intensity_image
    )

    measurements = [f.extract()]

    if plot:
        figure = f.plot()
    else:
        figure = str()

    return Output(measurements, figure)
