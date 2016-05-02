.. _installation:

************
Installation
************

`TissueMAPS` is designed to run on a server within a `SLURM <http://slurm.schedmd.com/>`_ cluster environment. There are `Ansible playbooks <http://docs.ansible.com/ansible/playbooks.html>`_ for automatic installation and deployment on the `ubuntu <http://www.ubuntu.com/>`_ operating system. We have also tested the software on `OSX`.

All Python dependencies are installed via `pip <https://pip.pypa.io/en/stable/>`_. Non-python dependencies are installed via `apt-get <http://manpages.ubuntu.com/manpages/hardy/man8/apt-get.8.html>`_ on `ubuntu` and via `homebrew <http://brew.sh/>`_ on `OSX`. See `OSXEssentials <https://github.com/HackerMD/OSXEssentials>`_ on recommendations for setting up your mac.

If you want to install the library locally, we recommend using a virtual environment:

To this end, install `virtualenv <https://virtualenv.readthedocs.org/en/latest/>`_ and `virtualenvwrapper <https://virtualenvwrapper.readthedocs.org/en/latest/>`_ and set up your environment::

    $ pip install virtualenv
    $ pip install virtualenvwrapper

Add the following lines to your ``.bash_profile`` file::

    export WORKON_HOME=$HOME/.virtualenvs
    export PROJECT_HOME=$HOME/Devel
    source /usr/local/bin/virtualenvwrapper.sh

Create a virtual environment for all `TissueMAPS` dependencies::

    $ mkvirtualenv tmaps


.. warning::

    Anticipate some problems when you have `anaconda <http://docs.continuum.io/anaconda/pkg-docs>`_ installed; see `potential solution <https://gist.github.com/mangecoeur/5161488>`_.


Clone the repository from Github::

    $ git clone https://github.com/TissueMAPS/TmLibrary.git $HOME/tmlibrary

Activate the virtual environment and install the required Python packages::

    $ workon tmaps

Install pip if necessary::

    $ pip install pip --upgrade

Now, install all requirements::

    $ pip install -r $HOME/tmlibrary/requirements-1.txt
    $ pip install -r $HOME/tmlibrary/requirements-2.txt
    $ pip install -r $HOME/tmlibrary/requirements-3.txt
    $ pip install -r $HOME/tmlibrary/requirements-Darwin.txt
    $ pip install -r $HOME/tmlibrary/requirements-git.txt

Now install the library itself in developer mode (this will allow you to edit code without having to reinstall the library)::

    $ pip install -e $HOME/tmlibrary


.. _dependencies:

Dependencies
============

.. _vips:

Vips
----

 `VIPS <http://www.vips.ecs.soton.ac.uk/index.php?title=VIPS>`_ is a fast and memory efficient image processing library (`Libvips API <http://www.vips.ecs.soton.ac.uk/supported/current/doc/html/libvips/index.html>`_). `VIPS` also supports `OpenSlide <http://openslide.org/>`_ and with it many `virtual slide formats <http://openslide.org/formats/>`_.

.. code:: bash
    
    $ brew tap homebrew/science
    $ brew install vips --with-openslide


The Python API for `VIPS` is based on `GObject introspection <https://wiki.gnome.org/action/show/Projects/GObjectIntrospection?action=show&redirect=GObjectIntrospection>`_. 
To use `VIPS` from python, you also need to install the python package `pygobject <https://wiki.gnome.org/action/show/Projects/PyGObject?action=show&redirect=PyGObject>`_.
  
.. .. code:: bash

    $ brew install pygobject3
    $ brew install gobject-introspection


In order to be able to use it within the virtual environment, you need to create a soft link::

    $ cd $VIRTUALENVWRAPPER_HOOK_DIR/tmaps/lib/python2.7/site-packages
    $ ln -s /usr/local/lib/python2.7/site-packages/gi gi


The type definitions are therefore automatically loaded and can be used from within Python, but there are also some convenience functions that are added to the `Image` class and some other shortcuts (like the automatic conversions of Python strings like ``'horizontal'`` to the respective C constants). Note, however, that these convenience functions won't show up in the IPython console when TAB completing on the image object. The docs can still be displayed with ``?``, though.

For more information see `VIPS from Python <http://www.vips.ecs.soton.ac.uk/supported/current/doc/html/libvips/using-from-python.html>`_.

.. _opencv:

OpenCV
------

`OpenCV <http://opencv.org/>`_ is an extensive image processing and computer vision library that provides a Python interface.

.. code:: bash
    
    $ brew tap homebrew/science
    $ brew install opencv3
    $ echo /usr/local/opt/opencv3/lib/python2.7/site-packages >> /usr/local/lib/python2.7/site-packages/opencv3.pth


In order to be able to use it within the virtual environment, you need to create a soft link::

    $ cd $VIRTUALENVWRAPPER_HOOK_DIR/tmaps/lib/python2.7/site-packages/
    $ ln -s /usr/local/lib/python2.7/site-packages/opencv3.pth opencv3.pth


.. _bio-formats:

Bio-Formats
-----------

`Bio-Formats <http://www.openmicroscopy.org/site/products/bio-formats>`_ is a tool for reading and writing microscopic image data in a standardized way. It `supports many formats <http://www.openmicroscopy.org/site/support/bio-formats5.1/supported-formats.html>`_ and can thus be used to read images together with their corresponding metadata from different sources.

The library can be installed via homebrew (or other package managers).

.. code:: bash
    
    $ brew install bioformats

*TissueMAPS* also uses the Python implementation `python-bioformats <https://github.com/CellProfiler/python-bioformats>`_.

The file ``$VIRTUALENVWRAPPER_HOOK_DIR/tmaps/lib/python2.7/site-packages/bioformats/jars/loci_tools.jar`` file can be replaced by a more recent one, e.g. `version 5.1.3 <http://downloads.openmicroscopy.org/bio-formats/5.1.3/artifacts/loci_tools.jar>`_.


.. _simpleitk:

SimpleITK
---------

`SimpleITK <http://www.simpleitk.org/>`_ is based on the `insight segmentation and registration toolkit (ITK) <http://www.itk.org/>`_, an extensive suite of image analysis tools, which also provides Python wrappers.

.. code:: bash

    $ brew install simpleitk


.. _hdf5:

HDF5
----

`HDF5 <https://www.hdfgroup.org/HDF5/>`_ files are suited for storing large datasets. The library can be installed via homebrew (or other package managers). 

.. code:: bash
    
    $ brew tab homebrew/science
    $ brew install hdf5

The content of `HDF5` files can be conveniently inspected via the command line interface `h5ls <https://www.hdfgroup.org/HDF5/doc/RM/Tools.html#Tools-Ls>`_ or via the graphical user interface `HDFVIEW <https://www.hdfgroup.org/products/java/hdfview/index.html>`_.


.. _other:

Other
-----

.. code:: bash

    $ brew install time         # required by GC3Pie
