'''Jterator module for measuring Zernike features.'''
import collections
import jtlib.features

VERSION = '0.0.1'

Output = collections.namedtuple('Output', ['measurements', 'figure'])


def main(label_image, plot=False):
    '''Measures texture features for objects in `label_image` based
    on grayscale values in `intensity_image`.

    Parameters
    ----------
    label_image: numpy.ndarray[int32]
        label image with objects that should be measured
    plot: bool, optional
        whether a plot should be generated (default: ``False``)

    Returns
    -------
    jtmodules.measure_zernike.Output

    See also
    --------
    :py:class:`jtlib.features.Zernike`
    '''
    f = jtlib.features.Zernike(label_image=label_image)

    measurements = [f.extract()]

    if plot:
        figure = f.plot()
    else:
        figure = str()

    return Outputs(measurements, figure)
