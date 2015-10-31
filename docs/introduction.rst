.. _introduction:

************
Introduction
************

.. _overview:

Overview
========

`TissueMAPS` is a web-based, cluster-integrated tool for visualizing and analyzing large-scale microscopic image datasets.

Microscopy image datasets can easily amount to several terabytes, which makes it impractical to store and process them on a local computer. Instead, images  are often stored on a remote data volume and processed by cluster computing.

`TissueMAPS` runs on a virtual machine (*VM*) within a cloud, where it has access to a shared files system and a cluster computing infrastructure. Users interact with the program via the Internet.

.. image:: ./_static/TissueMAPS_overview.png
    :height: 400px

The web-based approach has the advantage that large datasets can be handled efficiently and conveniently from a remote computer via a standard web browser.

On the server side, `TissueMAPS` uses Python as a glue language and the `tmlib` Python package serves as a library for tasks related to image storage and processing. The library has an object-orientated design and provides classes for file system operations and interaction with the computer cluster.

.. _file-system-configuration:

File system configuration
=========================

The organizational unit of `TissueMAPS` is an `experiment`, which is represented by a directory on disk that holds the microscopic image files and related files for metadata, calculated statistics or extracted features.

.. _user-configuration-settings:

User configuration settings
---------------------------

The location of files on disk can be configure via an experiment-specific user configuration file in `YAML <http://yaml.org/>`_ format.

.. literalinclude:: ./../tmlib/user.cfg.template


By default, all files belonging to an experiment are stored within the root experiment folder. However, a user can overwrite these default locations.


.. _workflow:

Workflow
========

The data unit for visualization of images and the corresponding features is a `Layer`. `TissueMAPS` supports two types of layers and their generation requires different image processing steps:

**Channel** layers are comprised of the actual microscopic raster images. For interactive visualization via the web, images are converted into `zoomify <http://www.zoomify.com/>`_ format. These so called `pyramids <https://en.wikipedia.org/wiki/Pyramid_(image_processing)>`_ represent a large image by several smaller image tiles (stored in `JPEG <http://www.jpeg.org>`_ files) at different resolution levels. Only the tiles that are required for the current view are loaded and streamed to the client.

**Object** layers represent geometrical structures, such as cell segmentations or wells in a multi-well plate. They are rendered on the client side as vector graphics. The data that specifies the location of objects in the map as well as the corresponding features that describe properties of the objects are stored in `HDF5 <https://www.hdfgroup.org/HDF5/>`_ files. 


The generation of these layers from the microscopic images generally involves different processing :ref:`stages`, each of which is composed of a sequence of individual **steps**:

.. image:: ./_static/TissueMAPS_workflow.png
    :height: 400px


.. _stages:

Stages
------

A workflow `stage` is composed of several *steps* and each `step` corresponds to a subpackage of the `tmlib` package.

.. _image-conversion:

Image conversion
^^^^^^^^^^^^^^^^

- :doc:`metaextract <tmlib.metaextract>`: **Extraction of metadata from microscope files**
    Microscopes usually store images together with additional acquisition information in vendor-specific formats. These are often not understood by standard readers. The `Bio-Formats <https://www.openmicroscopy.org/site/products/bio-formats>`_ Java library is used to extract the metadata from heterogeneous image file formats. These are stored as `OMEXML <https://www.openmicroscopy.org/site/support/ome-model/ome-xml/index.html>`_ files according to the standardized `OME <https://www.openmicroscopy.org/site/support/ome-model/>`_ data model.

- :doc:`metaconfig <tmlib.metaconfig>`: **Configuration and complementation of metadata**
    The information that can be retrieved from individual image files is often not sufficient for automated processing in subsequent steps. In particular, information about the position of images within the scanned grid, which is required to stitch individual images together for the creation of an overview of the entire acquisition area, may not be available from image files, but rather needs to be provided by additional microscope-specific metadata files or user input. Metadata from these various resources is combined into a single *OMEXML* per image acquisition.

- :doc:`imextract <tmlib.imextract>`: **Extraction of images from files**
    Image files may contain more than one image. For example, images acquired at different *z*-resolutions are often stored in the same file. Some microscopes even store all images in a single file. 
    These formats are not practical, because they require specialized readers. In addition, it is desirable to apply image compression to save storage space. To these ends, each 2D plate is extracted from the original file and stored in a separate `PNG <http://www.libpng.org/pub/png/>`_ file. Optionally, images acquired at different *z*-resolutions (*z*-stacks) are projected to 2D. Note that mapping from source to target files is already created in the `metaconfig` step.

.. image-preprocessing:

Image preprocessing
^^^^^^^^^^^^^^^^^^^

- :doc:`corilla <tmlib.corilla>`: **Calculation of illumination statistics**
    Microscopic images generally display illumination artifacts. Correction of these artifacts is important for visualization and even more so for quantitative analysis of pixel intensity values. Illumination statistics are pre-calculated across all acquisition sites and stored in `HDF5 <https://www.hdfgroup.org/HDF5/>`_ files. They can later be applied to individual images for correction.

- :doc:`align <tmlib.align>`: **Image registration and alignment**
    Images may be acquired at different time points with a potential shift in x-y directions between acquisitions. In order to be able to overlay images from different *cycles*, images have to be registered and aligned. Shift statistics are pre-calculated for each acquisition site and stored as `JSON <http://www.json.org/>`_ files.

.. _pyramid-creation:

Pyramid creation
^^^^^^^^^^^^^^^^

- :doc:`illuminati <tmlib.illuminati>`: **Creation of image pyramids**
    Individual images are stitched together to one big overview image according the positional information provided by the obtained metadata. Images are also corrected for illumination artifacts and aligned if necessary based on the calculated illumination and shift statistics, respectively. Segmented objects get global IDs assigned and their locations within images are translated into global map coordinates. Channel images are stored in `JPEG <http://www.jpeg.org>`_.

.. _image-analysis:

Image analysis
^^^^^^^^^^^^^^

- :doc:`jterator <tmlib.jterator>`: **Image segmentation and feature extraction**
    Biologically meaningful objects (e.g. "cells") are detected in the images by segmentation and features can be extracted for the detected objects.
    To this end, users can build custom image analysis *pipelines* by combining available modules in a `CellProfiler <http://cellprofiler.org/>`_ like web interface. The outlines of segmented objects and the extracted features are stored in `HDF5 <https://www.hdfgroup.org/HDF5/>`_ files.


.. _building-workflows:

Building workflows
------------------

Programmatically, each step is represented by `GC3Pie tasks <http://gc3pie.readthedocs.org/en/latest/programmers/api/gc3libs/workflow.html#gc3libs.workflow.SequentialTaskCollection>`_, which can combined into larger automated workflows. Individual steps are added to the :ref:`workflow` dynamically at runtime, but the steps can be configured in advance via a configuration settings file. To this end, the user needs to provide the required arguments for each step and can overwrite default settings for optional arguments.

For the list of arguments that can be parsed to each step please refer to the documentation of the *args* module in the corresponding package.

.. _command-line-interface:

Command-line interface
----------------------

Each `step` provides a command-line interface (**CLI**) with a similar syntax:

.. code-block:: bash

    <step> <general_args> <method> <specific_args>


The ``-h`` or ``--help`` argument can be used to get help for a particular step:

.. code-block:: bash
    
    <step> --help

It can also be used to get help for individual methods available for a particular step:

.. code-block:: bash

    <step> <genarl_args> <method> --help

.. note::

    General positional arguments have to be provided to display the help message for a particular method.


By default, each step is equipped with the following methods:

* **init**: initialize a step and create persistent job descriptions
* **run**: run an individual job on the local machine
* **submit**: submit all jobs to the cluster and continuously monitor their status (performs all *runs* in parallel)
* **cleanup**: remove all outputs created by previous *runs*/*submissions*

Some steps may provide additional methods, such as:

* **collect**: collect the job output of parallel *runs* and fuse the data spread across individual files into a single dataset if necessary
* **apply**: apply statistics calculated by the step to individual images

.. _example:

Example
^^^^^^^

.. code-block:: bash
    
    metaconfig -v ./ init --file_format cellvoyager


would initialize the `metaconfig` step and create persistent job descriptions on disk, which could subsequently be used to *run* or *submit* jobs. It further specifies a custom file format for the configuration of image metadata. 

