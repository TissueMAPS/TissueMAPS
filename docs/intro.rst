.. _introduction:

************
Introduction
************

**tmt** is a Python package that bundles image processing and data analysis tools for `TissueMAPS <https://github.com/HackerMD/TissueMAPS>`_.

.. _subpackages:

Subpackages
===========

**align** - Alignment of images between different acquisition cycles.

**corilla** - Correction of illumination artifacts.

**dafu** - Data fusion for `Jterator <https://github.com/HackerMD/Jterator>`_ projects.

**illuminati** - Creation of image pyramids.

**visi** - Conversion of Visitron's STK files to PNG images with optional renaming.


.. _configurationsettings:

Configuration settings
======================

Configurations are defined in *.config* `YAML <http://yaml.org/>`_ files to specify the experiment layout, such as the directory structure on disk.

Paths and filenames are described with `Python format strings <https://docs.python.org/2/library/string.html#formatstrings>`_. The **replacement fields** surrounded by curly braces ``{}`` are then automatically replaced with experiment specific variables.

To this end, you can use the following *replacement fields*:
    - *experiment_dir*: absolute path to the experiment directory
    - *experiment*: name of the experiment folder
    - *subexperiment*: name of a subexperiment folder, i.e. a subfolder of the experiment folder
    - *cycle*: number of a subexperiment
    - *channel*: number of a channel of intensity images (layers)
    - *objects*: name of objects in segmentation images (masks)

.. code:: yaml

    SUBEXPERIMENTS_EXIST: Yes

    # Path format strings
    IMAGE_FOLDER_LOCATION: '{experiment_dir}/{subexperiment}/images'
    SHIFT_FOLDER_LOCATION: '{experiment_dir}/{subexperiment}/shift'
    STATS_FOLDER_LOCATION: '{experiment_dir}/{subexperiment}/stats'
    SEGMENTATION_FOLDER_LOCATION: '{experiment_dir}/{subexperiment}/segmentations'
    LAYERS_FOLDER_LOCATION: '{experiment_dir}/layers'
    DATA_FILE_LOCATION: '{experiment_dir}/data.h5'

    # Filename format strings
    SUBEXPERIMENT_FOLDER_FORMAT: '{experiment}_{cycle:0>2}'
    SUBEXPERIMENT_FILE_FORMAT: '{experiment}_{cycle}'
    STATS_FILE_FORMAT: 'illumstats_channel{channel:0>3}.h5'
    SHIFT_FILE_FORMAT: 'shiftDescriptor.json'

    # Regular expression patterns to extract information encoded in filenames
    EXPERIMENT_FROM_FILENAME: '^([^_]+)'
    CYCLE_FROM_FILENAME: '_(\d+)_'
    COORDINATES_FROM_FILENAME: '_r(\d+)_c(\d+)_'
    COORDINATES_IN_FILENAME_ONE_BASED: Yes
    SITE_FROM_FILENAME: '_s(\d+)_'
    CHANNEL_FROM_FILENAME: 'C(\d+)\.png$'
    OBJECTS_FROM_FILENAME: '_segmented(\w+).png$'

    # Should Vips image processing library be used? Required for pyramid creation!
    USE_VIPS_LIBRARY: Yes

    # These settings are hard-coded in TissueMAPS, so don't change them!
    LAYERS_FOLDER_LOCATION: '{experiment_dir}/layers'
    ID_TABLES_FOLDER_LOCATION: '{experiment_dir}/id_tables'
    ID_PYRAMIDS_FOLDER_LOCATION: '{experiment_dir}/id_pyramids'
    DATA_FILE_LOCATION: '{experiment_dir}/data.h5'

..

    NOTE: Quotes are generally not required around strings in YAML syntax, but are necessary here because of the curly braces in the format strings!


.. _documentation:

Documentation
=============

`Sphinx <http://sphinx-doc.org/index.html>`_ is used for the documentation of source code in combination with the `Napoleon extension <https://pypi.python.org/pypi/sphinxcontrib-napoleon>`_ to support the `reStructuredText NumPy style <https://github.com/numpy/numpy/blob/master/doc/HOWTO_DOCUMENT.rst.txt#docstring-standard>`_.


Documentation is located under `docs` and will ultimately be hosted on `Read the Docs <https://readthedocs.org/>`_.

To update the documentation upon changes in the source code, do

.. code:: bash

    sphinx-apidoc -o ./docs ./tmt

To build HTML, do

.. code:: bash
    
    cd docs
    make html

The generated HTML files are located at `docs/_build/html`.
