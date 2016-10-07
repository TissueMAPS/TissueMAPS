.. _introduction:

************
Introduction
************

.. _overview:

Overview
========

`TissueMAPS` provides a computational framework for interactive visualization and analysis of large-scale microscopy image datasets.

High-throughput image-based screens generate terabytes of image data, which make it impractical to store and process the resulting data on a local computer and calls for remote storage and processing solutions instead.

In contrast to most available image processing applications, which are designed to run on a single desktop computer, `TissueMAPS` uses a distributed client-server model optimized for running on multiple virtual machines (VMs) in a modern cloud infrastructure.


.. image:: ./_static/overview.png
    :height: 300px

The software provides a user-friendly browser-based frontend and a scalable backend for processing terabyte-sized image datasets in an interactive and responsive manner.

.. _client-server-architecture:

Client-server architecture
==========================

The `TissueMAPS` server exposes a `RESTful API <https://en.wikipedia.org/wiki/Representational_state_transfer>`_ that abstracts away the complexity of the underlying compute and storage infrastructure. Clients send `HTTP <https://en.wikipedia.org/wiki/Hypertext_Transfer_Protocol>`_ request messages to the server, who handles the requests and returns response messages.

Active programming and command line interfaces are also available and allow advanced users to interact more programmatically with compute and storage resources.

As a consequence of its distributed nature, the different components of the application may not necessarily run on the same machine. To facilitate deployment and installation, code is partitioned into different packages and hosted by separate repositories.

.. _client:

Client
------

The `TmClient <https://github.com/TissueMAPS/TmClient>`_ repository hosts client `HTTP` interfaces implementated in different languages: a `Javascript <https://www.javascript.com/>`_ application is available for the web browser as well as `Python <https://www.python.org/>`_, `Matlab <https://mathworks.com/products/matlab/>`_ and `R <https://www.r-project.org/>`_ packages for programmatic upload and download of data.

.. _server:

Server
------

The server backend is implemented in `Python <https://www.python.org/>`_. The `TmServer <https://github.com/TissueMAPS/TmServer>`_ repository holds the web server application for handling client requests. The actual processing is delegated in most cases to either `TmLibrary <https://github.com/TissueMAPS/TmLibrary>`_ or `TmToolbox <https://github.com/TissueMAPS/TmToolbox>`_, which provide interfaces for distributed image processing workflows and interactive data analysis tools, respectively.

Python is a well-established general purpose language with great packages for scientific computing, image processing and machine learning. It is widely used in the scientific community and easy to learn for Biologists. `TissueMAPS` represents a compromise between abstraction and performance, emphasizing usability and rapid development, while enabling efficient processing of big datasets. It uses a modular object-oriented design that makes extension and customization straight forward. The server-client model enforces a strict separation of graphical user interface (GUI) handling and actual processing, resulting in more resource-optimized code for headless execution in a distributed environment.


.. _browser-based-user-interface:

Browser-based user interface
============================

`TissueMAPS` provides a web application implemented in `AngularJS <https://angular.io/>`_, which serves users as an interface for interactive and responsive visualization and analysis of their experiments.

The main components of the user interface are outlined below. For a detailed instruction, please refer to the :doc:`user guide <user_guide>`_.

.. _viewer:

Viewer
------

At the heard of the `TissueMAPS`' frontend lies the interactive *map* for multi-scale representation of 5D microsopy image data. It enables users to browse multi-channel raster images across different resolution levels and time points and overlay segmented objects as vector graphics.
Image datasets are generally too big to be served to the client en bloc. Therefore, datasets are tiled up and dynamically streamed from the server for display. The client only requests the subset of raster and vector tiles relevant for the current view and renders and caches them efficiently on the local graphics card via `WebGL <https://www.khronos.org/webgl/>`_. This results in a smooth user experience with reduced bandwidth.
Key features are support for brightfield and fluorescence mode, toggling and colorization of different channels and objects as well as instant intensity scaling and opacity adaptation for individual channels and object types, respectively.

.. TODO: screenshot

In addition to interactive visualization, there are tools for visually assisted data analysis and machine learning. These plugins allow users to select objects on the *map*, query information about them and subject them to to further analysis. Users can, for example, colorcode objects according to existing feature values or on the fly computed classification labels or visualize objects in multivariate feature space alongside their spatial *map* represenation.

.. TODO: screenshot

.. _workflow-manager:

Workflow Manager
----------------

The zoomable multi-scale representation requires pre-generated overview images in form of tiled `pyramids <https://en.wikipedia.org/wiki/Pyramid_(image_processing)>`_. In addition, objects of interest need to be computationally identified and measured by means of image segmentation and feature extraction, respectively, before they can be displayed on the *map* and used for further analyis.

Generally, serveral interdependent processing steps are required to get from the raw images to the final dataset. `TissueMAPS` provides a user-friendly interface to setup automated image analysis workflows, submit them for distributed processing, monitor the status of submitted computational jobs and report their results upon completion.

.. TODO: screenshot, links to tmlib.workflow

.. _distributed-image-processing-workflow:

Distributed image processing workflow
=====================================

A `TissueMAPS` workflow represents a series of *steps*, each of which comprises a set of computational *jobs* that get distributed across available compute resources for parallel processing. Functionally related *steps* are further grouped into abstract *stages*.

The :doc:`tmlib.workflow <tmlib.workflow>` package provides functionality for defining and managing distributed image processing workflows. The following "canonical" workflow for automated analysis of multi-wellplate screens is already implemented and used here for illustration. Custom workflows can be easily created to meet specific user requirements by either modifying or extending existing workflows or creating new ones from scratch.

.. _stages:

Stages
------

.. image:: ./_static/canonical_workflow.png
    :height: 300px

Note that "upload" and "download" stages are available in the user interface, but are not part of the actual image processing workflow and handled separately.


.. _image-conversion:

Image conversion
^^^^^^^^^^^^^^^^

Microscopes usually store pixel data together with related acquisition metadata in vendor-specific formats. These are often not understood by standard readers and generally not optimized for scalable storage in a distributed computing environment. The "image conversion" stage extracts individual pixel planes and associated metadata from microscopic image files and stores them in a consistent way to facilitate downstream processing.

- :doc:`metaextract <tmlib.workflow.metaextract>`: **Extraction of metadata**
    The `Bio-Formats <https://www.openmicroscopy.org/site/products/bio-formats>`_ Java library is used to extract metadata from heterogeneous image file formats, which is stored in `OMEXML <https://www.openmicroscopy.org/site/support/ome-model/ome-xml/index.html>`_ format according to the standardized `OME <https://www.openmicroscopy.org/site/support/ome-model/>`_ data model.

- :doc:`metaconfig <tmlib.workflow.metaconfig>`: **Configuration of metadata**
    Extracted metadata is often incomplete. In particular, the relative position of images, which is required for creation of pyramids, is typically not available from individual image files, but needs to be obtained from additional microscope-specific metadata files or user input.

- :doc:`imextract <tmlib.workflow.imextract>`: **Extraction of image data**
    Image files may contain more than one pixel plane. For example, planes acquired at different *z*-resolutions are often stored in the same file and some microscopes even store all planes in a single file. This is not practical and may even become a bottleneck depending on file access patterns and implemented storage backend.
    In addition, microscopes typically store images uncompressed, while it is often desirable to apply compression to reduce storage requirements. To meet these ends, each pixel plane is extracted from microscope files and stored separately. Optionally, images acquired at different *z*-resolutions are projected to 2D.

Note that implementation details of the storage backend may be subject to change and files may not necessarily accessible via a POSIX compliant file system! Users are therefore advised to use the `RESTful API` to request images from server.

.. _image-preprocessing:

Image preprocessing
^^^^^^^^^^^^^^^^^^^

Microscopic images typically contain artifacts that need to be assessed and corrected.

- :doc:`corilla <tmlib.workflow.corilla>`: **Calculation of illumination statistics**
    Microscopic images generally display illumination illumination. Correction of these artifacts is important for visualization and even more so for quantitative analysis of pixel intensities. Illumination statistics are calculated across all acquisition sites and stored. They can later be applied to individual images to correct illumination artifacts or uniformly rescale intensities across images.

- :doc:`align <tmlib.workflow.align>`: **Image registration and alignment**
    Images acquired at the different time points may exhibit a displacement relative to each other and need to be aligned to overlay them for visualization or analysis. To this end, images are registered between different acquisitions and the computed shifts are stored for subsequent alignment.

.. _pyramid-creation:

Pyramid creation
^^^^^^^^^^^^^^^^

- :doc:`illuminati <tmlib.workflow.illuminati>`: **Image pyramid creation**
    For efficient zoomable browser-based visualization, images are casted to 8-bit and tiled according the positional information obtained in the `image conversion <image-conversion>`_ *stage*. Users further have the option to correct images for illumination artifacts and align them between acquisitions based on statistics calculated in the `image preprocessing <image-preprocessing>`_ *stage*.

.. _image-analysis:

Image analysis
^^^^^^^^^^^^^^

- :doc:`jterator <tmlib.workflow.jterator>`: **Image segmentation and feature extraction**
    The objective of image analysis is to identify biologically meaningful objects (e.g. "cells") in the images and extract features for identified objects.
    To this end, users can combine individual modules available in the `JtModules repository <https://github.com/TissueMAPS/JtModules>`_ into a custom image analysis *pipelines* in a `CellProfiler <http://cellprofiler.org/>`_ like manner. Outlines of segmented objects and extracted features can be stored for further analyis. Once stored, they are automatically available for in the user interface and can be downloaded from the server.
