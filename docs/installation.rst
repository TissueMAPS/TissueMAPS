.. _installation:

************
Installation
************

First, clone the repository::

    $ git clone https://github.com/HackerMD/TissueMAPSToolbox.git ~/tmapstoolbox

Then, create a virtual environment:

To this end, install `virtualenv` and `virtualenvwrapper` and set up your environment::

    $ pip install virtualenv
    $ pip install virtualenvwrapper

Add the following lines to your ``.bash_profile`` file::

    export WORKON_HOME=$HOME/.virtualenvs
    export PROJECT_HOME=$HOME/Devel
    source /usr/local/bin/virtualenvwrapper.sh

Create the virtual environment::

    $ mkvirtualenv tmt

Activate the virtual environment and run the installation of required packages::
    $ workon tmt
    $ pip install numpy
    $ pip install scipy
    $ pip install -r ~/tmapstoolbox/requirements.txt


.. _dependencies:

Dependencies
============

On *OSX* use `homebrew <http://brew.sh/>`_ for the installation of the dependencies listed below. See `OSXEssentials <https://github.com/HackerMD/OSXEssentials>`_ on recommendations for setting up your mac.

.. _vips:

Vips
----

 `VIPS <http://www.vips.ecs.soton.ac.uk/index.php?title=VIPS>`_ is a fast and memory efficient image processing library (`Libvips API <http://www.vips.ecs.soton.ac.uk/supported/current/doc/html/libvips/index.html>`_). The library can be installed via homebrew (or other package managers). 

On Mac OSX:

.. code:: bash
    
    $ brew tab homebrew/science
    $ brew install vips


The Python API for `VIPS` is based on `GObject introspection <https://wiki.gnome.org/action/show/Projects/GObjectIntrospection?action=show&redirect=GObjectIntrospection>`_. 
To use `VIPS` from python, you also need to install the python package `pygobject <https://wiki.gnome.org/action/show/Projects/PyGObject?action=show&redirect=PyGObject>`_.
  
.. code:: bash

    $ brew install pygobject3


In order to be able to use it within the virtual environment, you need to create a soft link::

    $ cd $VIRTUALENVWRAPPER_HOOK_DIR/tmaps/lib/python2.7/site-packages/gi
    $ ln -s /usr/local/lib/python2.7/site-packages/gi gi


The type definitions are therefore automatically loaded and can be used from within Python, but there are also some convenience functions that are added to the `Image` class and some other shortcuts (like the automatic conversions of Python strings like ``'horizontal'`` to the respective C constants).
In IPython these convenience functions won't show up when TAB completing on the image object. For example:

The C function

.. code:: python

    int
    vips_add (VipsImage *left,
              VipsImage *right,
              VipsImage **out,
              ...);

is added to the Python image objects, but won't show up. The docs can still be displayed with ``?img.add``, however.

For more information see `VIPS from Python <http://www.vips.ecs.soton.ac.uk/supported/current/doc/html/libvips/using-from-python.html>`_.

It may also be helpful to look into the `VIPS function list <http://www.vips.ecs.soton.ac.uk/supported/current/doc/html/libvips/func-list.html>`_.


    NOTE: The `illuminati` package depends on `VIPS`, but the other routines also work without `VIPS` and use `numpy` instead if you set ``USE_VIPS_LIBRARY`` to "No".

.. _opencv:

OpenCV
------

`OpenCV <http://opencv.org/>`_ is ...

On Mac OSX:

.. code:: bash
    
    $ brew tab homebrew/science
    $ brew install opencv3
    $ echo /usr/local/opt/opencv3/lib/python2.7/site-packages >> /usr/local/lib/python2.7/site-packages/opencv3.pth


In order to be able to use it within the virtual environment, you need to create a soft link::

    $ cd $VIRTUALENVWRAPPER_HOOK_DIR/tmaps/lib/python2.7/site-packages/
    $ ln -s /usr/local/lib/python2.7/site-packages/opencv3.pth opencv3.pth


On Linux (Ubuntu):

See http://rodrigoberriel.com/2014/10/installing-opencv-3-0-0-on-ubuntu-14-04/


.. _simpleitk:

SimpleITK
---------

`SimpleITK <http://www.simpleitk.org/>`_ is ...


.. _hdf5:

HDF5
----

Data are stored in `HDF5 <https://www.hdfgroup.org/HDF5/>`_ files. The library can be installed via homebrew (or other package managers). 

On Mac OSX:

.. code:: bash
    
    $ brew tab homebrew/science
    $ brew install hdf5

The content of `HDF5` files can be conveniently inspected via the command line interface `h5ls <https://www.hdfgroup.org/HDF5/doc/RM/Tools.html#Tools-Ls>`_ or via the graphical user interface `HDFVIEW <https://www.hdfgroup.org/products/java/hdfview/index.html>`_.


Configuration
=============

gc3pie
------

With *GC3Pie* you can run computational tasks "jobs" on your local machine as well as in diverse cluster and cloud environments. To process jobs in parallel, you need to configure some settings regarding your computational environment.

You can create an example configuration file by simply calling any gc3pie command, e.g.::

    $ gserver

This will create the file ``$HOME/.gc3/gc3pie.conf``. Modify it according to your needs. For more information please refer to the `GC3Pie online documentation <http://gc3pie.readthedocs.org/en/latest/users/configuration.html>`_
