.. _gettingstarted:

***************
Getting started
***************

.. _installation:

Installation
============

Clone the repository

.. code:: bash

    $ git clone https://github.com/HackerMD/TissueMAPSToolbox.git ~/tmapstoolbox

and install it

.. code:: bash
    
    $ cd ~/tmapstoolbox/tmt
    $ pip install -e .


.. _dependencies:

Dependencies
============

Vips
----

 Images are processed with `VIPS <http://www.vips.ecs.soton.ac.uk/index.php?title=VIPS>`_, a fast and memory efficient image processing library (`API <http://www.vips.ecs.soton.ac.uk/supported/current/doc/html/libvips/index.html>`_). The library can be installed via homebrew (or other package managers). 

On Mac OSX:

.. code:: bash
    
    $ brew tab homebrew/science
    $ brew install vips


Since `VIPS` is used from python, you also need to install the required python package `pygobject <https://wiki.gnome.org/action/show/Projects/PyGObject?action=show&redirect=PyGObject>`_.
  
.. code:: bash

    $ pip install pygobject3


You also need to set the ``GI_TYPELIB_PATH`` variable.


The Python API for `VIPS` is based on `GObject introspection <https://wiki.gnome.org/action/show/Projects/GObjectIntrospection?action=show&redirect=GObjectIntrospection>`_. The type definitions are therefore automatically loaded and can be used from within Python, but there are also some convenience functions that are added to the `Image` class and some other shortcuts (like the automatic conversions of Python strings like ``'horizontal'`` to the respective C constants).
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


    NOTE: The `illuminati` package depends on `VIPS`, but the other routines also work without `VIPS` and use `numpy` instead if you set ``USE_VIPS_LIBRARY`` to 'No'.


HDF5
----

Data are stored in `HDF5 <https://www.hdfgroup.org/HDF5/>`_ files. The library can be installed via homebrew (or other package managers). 

On Mac OSX:

.. code:: bash
    
    $ brew tab homebrew/science
    $ brew install hdf5

The content of `HDF5` files can be conveniently inspected via the command line using `h5ls <https://www.hdfgroup.org/HDF5/doc/RM/Tools.html#Tools-Ls>`_ or via the graphical user interface `HDFVIEW <https://www.hdfgroup.org/products/java/hdfview/index.html>`_.
