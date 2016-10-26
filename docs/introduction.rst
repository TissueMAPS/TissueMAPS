.. _introduction:

************
Introduction
************

.. _what-is-tissuemaps:

What is TissueMAPS?
===================

`TissueMAPS` is a computational framework for interactive visualization and analysis of large-scale microscopy image datasets.

High-throughput image-based screens amount to terabytes of image data. The size of the generated datasets make it impractical to store and process data on a local computer, but rather calls for remote solutions.

Most available applications for microscopy image analysis are designed to run on a single desktop computer.
`TissueMAPS` instead uses a distributed client-server model optimized for processing images in parallel on multiple virtual machines (VMs) in a modern cloud infrastructure.

.. _client-server-architecture:

Client-server architecture
==========================

.. image:: ./_static/overview.png
    :height: 300px

The software combines a intuitive, user-friendly browser-based frontend with a scalable backend to process multi-terabyte image datasets in an interactive and responsive manner.

The `TissueMAPS` server exposes a `RESTful API <https://en.wikipedia.org/wiki/Representational_state_transfer>`_ that abstracts away the complexity of compute and storage infrastructure. Clients send `HTTP <https://en.wikipedia.org/wiki/Hypertext_Transfer_Protocol>`_ request messages to the server, who handles the requests and returns response messages. The server processes request asynchronenous by submitting computational tasks to available compute resources.

In addition to the `HTTP` interface, `TissueMAPS` provides extensive active programming (API) and command line interfaces (CLI) that allow advanced users to interact more programmatically with the data and underlying infrastructure.

As a consequence of its distributed nature, the different components of the application may not necessarily run on the same machine. To facilitate deployment and installation, code is partitioned into different packages and hosted by separate repositories.

.. _client-code:

Client code
-----------

Client `HTTP` interfaces are implementated in different languages.

The `TmUI <https://github.com/TissueMAPS/TmUI>`_ repository holds the `Javascript <https://www.javascript.com/>`_ code for the browser-based user interface implemented in form of an `AngularJS <https://angularjs.org/>`_ app. Although it represents client code, this repository is installed server side, since the code is served to clients upon request via the browser.

The `TmClient <https://github.com/TissueMAPS/TmClient>`_ repository holds `Python <https://www.python.org/>`_, `Matlab <https://mathworks.com/products/matlab/>`_ and `R <https://www.r-project.org/>`_ packages for programmatic interaction with the server, e.g. for upload and download of data. This code gets installed directly on client machines.

.. _server-code:

Server code
-----------

The server backend is implemented in `Python <https://www.python.org/>`_ - a well-established general purpose language with powerful packages for scientific computing (`NumPy <http://www.numpy.org/>`_, `Pandas <http://pandas.pydata.org/>`_), image processing (`Mahotas <http://mahotas.readthedocs.io/en/latest/>`_, `OpenCV <http://docs.opencv.org/3.1.0/d6/d00/tutorial_py_root.html>`_) and machine learning (`Scikit-Learn <http://scikit-learn.org/stable/>`_, `Theano <http://deeplearning.net/software/theano/>`_, `PySpark <http://spark.apache.org/docs/0.9.0/python-programming-guide.html>`_). It is widely used in the scientific community and easy to learn for Biologists.

The `TmServer <https://github.com/TissueMAPS/TmServer>`_ repository holds the server application for handling client requests. The actual processing is delegated to either `TmLibrary <https://github.com/TissueMAPS/TmLibrary>`_ or `TmToolbox <https://github.com/TissueMAPS/TmToolbox>`_, which provide interfaces for distributed image processing workflows and interactive data analysis tools, respectively.

`TissueMAPS` represents a compromise between abstraction and performance, emphasizing usability and rapid development, while enabling efficient processing of big datasets. It uses a modular object-oriented design to facilitate extension and customization. The server-client model enforces a strict separation of graphical user interface (GUI) handling and actual processing, resulting in more resource-optimized code for headless execution in a distributed environment.


.. _browser-based-user-interface:

Browser-based user interface
============================

.. _viewer:

Viewer
------

At the heard of the `TissueMAPS`' frontend lies the interactive *map* for multi-scale representation of 5D microsopy image data. It enables users to browse multi-channel raster images across different resolution levels and time points and overlay segmented objects as vector graphics.
Image datasets are generally too big to be served to the client en bloc. Therefore, datasets are tiled up and dynamically streamed from the server for display. The client only requests the subset of raster and vector tiles relevant for the current view and renders and caches them efficiently on the local graphics card via `WebGL <https://www.khronos.org/webgl/>`_. This results in a smooth user experience with reduced bandwidth.
Key features are support for brightfield and fluorescence mode, toggling and colorization of different channels and objects as well as instant intensity scaling and opacity adaptation for individual channels and object types, respectively.

.. TODO: screenshot

.. _data-anlysis-tools:

Data analysis tools
-------------------

In addition to interactive visualization, there are plugins for visually assisted data analysis and machine learning. These tools allow users to select objects on the *map*, query information about them and subject them to to further analysis. Users can, for example, colorcode objects according to existing feature values or on the fly computed classification labels or visualize objects in multivariate feature space alongside their spatial *map* represenation.

.. TODO: screenshot

.. _workflow-manager:

Workflow Manager
----------------

The zoomable multi-scale representation requires pre-generated overview images in form of tiled `pyramids <https://en.wikipedia.org/wiki/Pyramid_(image_processing)>`_. In addition, objects of interest need to be computationally identified and measured by means of image segmentation and feature extraction, respectively, before they can be displayed on the *map* and used for further analyis.

Generally, serveral interdependent processing steps are required to get from the raw images to the final dataset. `TissueMAPS` provides a user-friendly interface to setup automated image analysis workflows, submit them for distributed processing, monitor the status of submitted computational jobs and report results and statistics upon completion.

.. TODO: screenshot, links to tmlib.workflow

.. _distributed-image-processing:

Distributed image processing
============================

A `TissueMAPS` image processing workflow represents a series of *steps*, each of which comprises a set of computational *jobs* that get distributed across available compute resources for parallel processing. Functionally related *steps* are further grouped into abstract *stages*.

The :doc:`tmlib.workflow <tmlib.workflow>` package provides functionality for defining and managing distributed image processing workflows. The following "canonical" workflow for automated analysis of multi-wellplate screens is already implemented and used here for illustration. To meet specific user requirements, custom workflows can be easily created, either by modifying or extending existing workflows or creating new ones from scratch.

.. _canonical-workflow:

Canonical workflow
------------------

.. image:: ./_static/canonical_workflow.png
    :height: 300px

Note that "upload" and "download" stages are available in the user interface, but are not part of the actual image processing workflow and consequently handled separately.


.. _image-conversion:

Image conversion
^^^^^^^^^^^^^^^^

- :doc:`metaextract <tmlib.workflow.metaextract>`: **Extraction of metadata**

- :doc:`metaconfig <tmlib.workflow.metaconfig>`: **Configuration of metadata**

- :doc:`imextract <tmlib.workflow.imextract>`: **Extraction of image data**

.. _image-preprocessing:

Image preprocessing
^^^^^^^^^^^^^^^^^^^

Microscopic images typically contain artifacts that need to be assessed and corrected.

- :doc:`corilla <tmlib.workflow.corilla>`: Calculation of illumination statistics

- :doc:`align <tmlib.workflow.align>`: Image registration and alignment

.. _pyramid-creation:

Pyramid creation
^^^^^^^^^^^^^^^^

- :doc:`illuminati <tmlib.workflow.illuminati>`: Image pyramid creation

.. _image-analysis:

Image analysis
^^^^^^^^^^^^^^

- :doc:`jterator <tmlib.workflow.jterator>`: Image segmentation and feature extraction


.. _distributed-machine-learning:

Distributed machine learning
============================


.. TODO
