from __future__ import unicode_literals
import sys
import yaml
import h5py
import mpld3


def readconfig(configuration):
    '''
    Reading configuration settings from YAML string.

    Parameters
    ----------
    configuration: str
        configuration settings

    Returns
    -------
    dict
    '''
    pyfilename = sys._getframe().f_code.co_name
    config = yaml.load(configuration)
    print('jt -- %s: read configuration settings from "%s"'
          % (pyfilename, configuration))
    return config


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
    pyfilename = sys._getframe().f_code.co_name
    hdf5_data = h5py.File(data_file, 'r+')
    for key in data:
        hdf5_location = key
        hdf5_data.create_dataset(hdf5_location, data=data[key])
        print('jt -- %s: wrote dataset \'%s\' to HDF5 location: "%s"'
              % (pyfilename, key, hdf5_location))
    hdf5_data.close()


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
    pyfilename = sys._getframe().f_code.co_name
    mousepos = mpld3.plugins.MousePosition(fontsize=20)
    mpld3.plugins.connect(fig, mousepos)
    mpld3.save_html(fig, figure_file)   # template_type='simple'
    print('jt -- %s: wrote figure to HTML file: "%s"'
          % (pyfilename, figure_file))
