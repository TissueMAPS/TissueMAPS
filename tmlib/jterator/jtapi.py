import mpld3
import logging
from ..readers import DatasetReader

logger = logging.getLogger(__name__)


def writedata(data, data_file):
    '''
    Writing data to HDF5 file.

    For each key, value pair the key will define the name of the dataset
    and the value will be stored as the actual dataset.

    Parameters
    ----------
    data: Dict[str, numpy.ndarray]
        data that should be saved
    data_file: str
        path to the data file
    '''
    with DatasetReader(data_file) as f:
        for key in data:
            hdf5_location = key
            logger.debug('write dataset \'%s\' to HDF5 location: "%s"'
                        % (key, hdf5_location))
            f.write(hdf5_location, data=data[key])


def savefigure(fig, figure_file):
    '''
    Writing figure instance to file as HTML string with embedded javascript
    code (using the `mpld3 <http://mpld3.github.io/>`_ package).

    Parameters
    ----------
    fig: matplotlib.figure.Figure
        figure instance
    figure_file: str
        name of the figure file
    '''
    mousepos = mpld3.plugins.MousePosition(fontsize=20)
    mpld3.plugins.connect(fig, mousepos)
    logger.debug('write figure to HTML file: "%s"' % figure_file)
    mpld3.save_html(fig, figure_file)   # template_type='simple'
