import numpy as np
import pylab as plt
import os
import collections
import tmt
from jterator import jtapi
from tmt.project import Project
from tmt.image import ChannelImage


def correct(InputImage, InputImageFilename, Smooth, Sigma, Config=None,
            **kwargs):
    '''
    Jterator module for correcting an image
    for illumination artifacts using pre-calculated statistics.

    Parameters
    ----------
    InputImage: numpy.ndarray[float64]
        grayscale image that should be corrected
    InputImageFilename: str
        corresponding filename of the image
    Smooth: bool
        whether statistics image should be smoothed prior to correction
        (may reduce overcorrection artifacts at the border of the image)
    Config: dict
        configuration settings
    **kwargs: dict
        additional arguments provided by Jterator:
        "ProjectDir", "DataFile", "FigureFile", "Plot"

    Returns
    -------
    namedtuple[numpy.ndarray]
        corrected image: "CorrectedImage"

    See also
    --------
    `illumstats.Illumstats`
    `illumstats.illum_correct`
    '''

    assert InputImage.dtype == 'float64', \
        ('Image has wrong data type. '
         'It must have "float64" but has "%s" instead.' % InputImage.dtype)

    if Config:
        cfg = jtapi.readconfig(Config)
    else:
        cfg = tmt.config

    # retrieve pre-calculated statistics
    channel_number = ChannelImage(InputImageFilename, cfg).channel
    # we assume here that the project path is one level up
    # relative to the Jterator project
    project = Project(os.path.dirname(kwargs['ProjectDir']), cfg)
    stats = [f for f in project.stats_files if f.channel == channel_number][0]

    # apply statistics for illumination correction
    mean_img = stats.mean_image
    std_img = stats.std_image
    img = stats.correct(InputImage, smooth=Smooth, sigma=Sigma)

    if kwargs['Plot']:

        fig = plt.figure(figsize=(10, 10))

        rescale_lower = np.percentile(InputImage, 0.1)
        rescale_upper = np.percentile(InputImage, 99.9)

        ax1 = fig.add_subplot(2, 3, 1)
        ax1.imshow(InputImage, cmap='gray',
                   vmin=rescale_lower, vmax=rescale_upper)
        ax1.set_title('InputImage', size=20)

        ax2 = fig.add_subplot(2, 3, 2)
        ax2.imshow(img, cmap='gray',
                   vmin=rescale_lower, vmax=rescale_upper)
        ax2.set_title('CorrectedImage', size=20)

        ax3 = fig.add_subplot(2, 3, 3)
        ax3.imshow(mean_img, cmap='jet',
                   vmin=np.percentile(mean_img, 0.1),
                   vmax=np.percentile(mean_img, 99.9))
        ax3.set_title('Mean', size=20)

        ax4 = fig.add_subplot(2, 3, 4)
        ax4.hist(InputImage.flatten(), bins=100,
                 range=(rescale_lower, rescale_upper),
                 histtype='stepfilled')
        ax4.set_title('InputImage', size=20)

        ax5 = fig.add_subplot(2, 3, 5)
        ax5.hist(img.flatten(), bins=100,
                 range=(rescale_lower, rescale_upper),
                 histtype='stepfilled')
        ax5.set_title('CorrectedImage', size=20)

        ax6 = fig.add_subplot(2, 3, 6)
        ax6.imshow(std_img, cmap='jet',
                   vmin=np.percentile(std_img, 0.1),
                   vmax=np.percentile(std_img, 99.9))
        ax6.set_title('Std', size=20)

        jtapi.savefigure(fig, kwargs['FigureFile'])

    output = collections.namedtuple('Output', 'CorrectedImage')
    return output(img)
