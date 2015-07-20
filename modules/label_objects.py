# from skimage import measure
import mahotas as mh
import pylab as plt
import collections
from jterator import jtapi


def label_objects(InputImage, **kwargs):
    '''
    Jterator module for labeling connected components ("objects")
    in a binary image.
    For more information see
    `mahotas docs <http://mahotas.readthedocs.org/en/latest/labeled.html#labeling-images>`_.

    Parameters
    ----------
    InputImage: numpy.ndarray[bool]
        binary image that should labeled
    **kwargs: dict
        additional arguments provided by Jterator:
        "ProjectDir", "DataFile", "FigureFile", "Plot"

    Returns
    -------
    namedtuple[numpy.ndarray[int]]
        labeled image: "Objects"
    '''

    # img = measure.label(InputImage)
    img, n_objects = mh.label(InputImage)

    if kwargs['Plot']:

        fig = plt.figure(figsize=(10, 10))
        ax1 = fig.add_subplot(1, 2, 1)
        ax2 = fig.add_subplot(1, 2, 2)

        ax1.imshow(InputImage)
        ax1.set_title('InputImage', size=20)

        ax2.imshow(img)
        ax2.set_title('Objects', size=20)

        fig.tight_layout()

        jtapi.savefigure(fig, kwargs['FigureFile'])

    output = collections.namedtuple('Output', 'Objects')
    return output(img)
