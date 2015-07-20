import numpy as np
import pylab as plt
import collections
from tmt.project import Project
from jterator import jtapi


def align(InputImage, InputImageFilename, Config, **kwargs):
    '''
    Jterator module for the alignment of an image according to pre-calculated
    shift and overlap values. The image gets shifted and cropped.

    .. Warning::

        The output image may have different dimensions that the input image.

    Parameters
    ----------
    InputImage: numpy.ndarray
        image that should be aligned
    InputImageFilename: str
        corresponding filename of the image
    Config: dict
        configuration settings
    **kwargs: dict
        additional arguments provided by Jterator:
        "ProjectDir", "DataFile", "FigureFile", "Plot"

    Returns
    -------
    namedtuple[numpy.ndarray]
        aligned image: "AlignedImage"

    See also
    --------
    `shift.ShiftDescriptor`
    `shift.shift_and_crop_image`
    '''

    project = Project(kwargs['ProjectDir'], Config)
    img = project.shift_file.align(InputImage, InputImageFilename)

    if kwargs['Plot']:

        fig = plt.figure(figsize=(10, 10))
        ax1 = fig.add_subplot(1, 2, 1)
        ax2 = fig.add_subplot(1, 2, 2)

        ax1.imshow(InputImage, cmap='gray',
                   vmin=np.percentile(InputImage, 0.1),
                   vmax=np.percentile(InputImage, 99.9))
        ax1.set_title('InputImage', size=20)

        ax2.imshow(img, cmap='gray',
                   vmin=np.percentile(img, 0.1),
                   vmax=np.percentile(img, 99.9))
        ax2.set_title('SmoothedImage', size=20)

        fig.tight_layout()

        jtapi.savefigure(fig, kwargs['FigureFile'])

    output = collections.namedtuple('Output', 'AlignedImage')
    return output(img)
