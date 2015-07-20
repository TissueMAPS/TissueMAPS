import numpy as np
import pylab as plt
from mpl_toolkits.axes_grid1 import make_axes_locatable
import mpld3
import collections
from tmt.project import Project
from tmt.image import Image
from jterator import jtapi


def load_objects(RefImageFilename, ObjectsName, Config, **kwargs):
    '''
    Jterator module for loading a "label" image for particular objects
    from disk into memory in order to make it available to downstream modules.

    Parameters
    ----------
    RefImageFilename: str
        filename of the reference image
    ObjectsName: str
        name of the objects in the labeled segmentation image that should be
        loaded
    Config: dict
        configuration settings
    **kwargs: dict
        additional arguments provided by Jterator:
        "ProjectDir", "DataFile", "FigureFile", "Plot"

    Returns
    -------
    namedtuple[numpy.ndarray[int32]]
        loaded image: "Objects"
    '''
    Config['USE_VIPS_LIBRARY'] = False  # use numpy

    # determine current site from reference image
    current_site = Image(RefImageFilename, Config).site
    # load corresponding segmentation image for the specified objects
    project = Project(kwargs['ProjectDir'], Config)
    img = [f.image for f in project.segmentation_files
           if f.objects == ObjectsName and f.site == current_site][0]

    if len(img) > 0 or not img:
        raise IOError('Filename of the labeled segmentation image could not'
                      'be determined correctly from reference image filename '
                      'and objects name. Check your settings!')
    else:
        img = img[0]

    if kwargs['plot']:

        fig = plt.figure(figsize=(10, 10))
        ax = fig.add_subplot(1, 1, 1)

        rescale_lower = np.percentile(img, 0.1)
        rescale_upper = np.percentile(img, 99.9)

        im = ax.imshow(img, cmap='gray',
                       vmin=rescale_lower,
                       vmax=rescale_upper)
        ax.set_title(ObjectsName, size=20)

        divider = make_axes_locatable(ax)
        cax = divider.append_axes("right", size="5%", pad=0.05)
        fig.colorbar(im, cax=cax)
        fig.tight_layout()

        mousepos = mpld3.plugins.MousePosition(fontsize=20)
        mpld3.plugins.connect(fig, mousepos)
        mpld3.fig_to_html(fig, template_type='simple')

        jtapi.savefigure(fig, kwargs['FigureFile'])

    output = collections.namedtuple('Output', 'LoadedObjects')
    return output(img)
