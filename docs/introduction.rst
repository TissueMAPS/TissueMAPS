.. _introduction:

************
Introduction
************

.. _what-is-tissuemaps:

What is TissueMAPS?
===================

`TissueMAPS` is a computational framework for interactive visualization and analysis of large-scale microscopy image datasets.

High-throughput image-based screens amount to terabytes of image data. The size of the generated datasets make it impractical to store and process data on a local computer, but rather calls for remote scale-out solutions. This poses a challenges for biological researchers, who usually have little experience with distributed computing.

Available applications for microscopy image analysis are generally designed to run on a single desktop computer with a graphical user interface (GUI). Some expose a command line interace that allows running the program in headless mode, but users then loose the ability to interact visually with the image data.
`TissueMAPS` uses a distributed client-server model optimized for processing image data in parallel on multiple virtual machines (VMs) in a modern cloud infrastructure. It combines an intuitive, user-friendly browser-based frontend with a scalable backend to process multi-terabyte image datasets in an interactive and responsive manner.

.. _client-server-architecture:

Client-server architecture
==========================

.. figure:: ./_static/overview.png
   :height: 300px
   :align: left

   Computational infrastructure.

   The server backend may scale from a single standalone machine hosting web, storage and compute units to a large, scale-out grid consisting of several compute and storage clusters, where individual components are distributed over hundreds of dedicated machines. Only one client is shown here for simplicity, but of course multiple clients may interact simultaneously with the same server.


The `TissueMAPS` server exposes a `RESTful API <https://en.wikipedia.org/wiki/Representational_state_transfer>`_ that abstracts away the complexity of compute and storage infrastructure. Clients send `HTTP <https://en.wikipedia.org/wiki/Hypertext_Transfer_Protocol>`_ request messages to the server, who handles the requests and returns response messages to the client. The server processes these requests asynchronenous and submits computational tasks to available compute resources.

In addition to the `HTTP` interface, `TissueMAPS` provides extensive active programming (API) and command line interfaces (CLI) that allow users to interact more programmatically with the underlying infrastructure and the data.

As a consequence of its distributed nature, the different components of the application (web server, database server, compute units, ...) may not necessarily all run on the same machine. To facilitate setup and deployment, code is partitioned into different packages and hosted by separate repositories. The main `TissueMAPS <https://github.com/TissueMAPS/TissueMAPS>`_ repository combines the individual repositories at the latest stable release version.

.. _client-code:

Client code
-----------

Client `HTTP` interfaces are implementated in different languages.

The `TmUI <https://github.com/TissueMAPS/TmUI>`_ repository holds the `Javascript <https://www.javascript.com/>`_ code for the browser-based user interface, implemented as an `AngularJS <https://angularjs.org/>`_ app. Although technically client code, the app gets installed server side, since the code is served to clients upon request send by the browser.

The `TmClient <https://github.com/TissueMAPS/TmClient>`_ repository holds `Python <https://www.python.org/>`_, `Matlab <https://mathworks.com/products/matlab/>`_ and `R <https://www.r-project.org/>`_ packages for programmatic interaction with the server, e.g. for upload and download of data. These packages are light-weight REST API wrappers and have only very few dependencies. They get installed directly on client machines.

.. _server-code:

Server code
-----------

The `TmServer <https://github.com/TissueMAPS/TmServer>`_ repository holds the server application that handles client requests. The actual processing is delegated to the `tmlib` package provided via the `TmLibrary <https://github.com/TissueMAPS/TmLibrary>`_ repository.

The server backend is implemented in `Python <https://www.python.org/>`_ - a well-established general purpose language with powerful packages for scientific computing (`NumPy <http://www.numpy.org/>`_, `Pandas <http://pandas.pydata.org/>`_), image processing (`Mahotas <http://mahotas.readthedocs.io/en/latest/>`_, `OpenCV <http://docs.opencv.org/3.1.0/d6/d00/tutorial_py_root.html>`_) and machine learning (`Scikit-Learn <http://scikit-learn.org/stable/>`_, `Theano <http://deeplearning.net/software/theano/>`_, `PySpark <http://spark.apache.org/docs/0.9.0/python-programming-guide.html>`_). It is widely used in the scientific community and easy to learn for Biologists.

`TissueMAPS` represents a compromise between abstraction and performance, emphasizing usability and rapid development, while enabling efficient processing of big datasets. It uses a modular object-oriented design to facilitate extension and customization. The server-client model further enforces a strict separation of graphical user interface (GUI) handling and actual processing, which results in more resource-optimized code for headless execution in a distributed environment.


.. _browser-based-user-interface:

Browser-based user interface
============================

.. _viewer:

Viewer
------

At the heard of the `TissueMAPS` lies an interactive viewer for multi-scale representation of 5D microsopy image data. It enables users to browse multi-channel raster images across different resolution levels and time points and overlay segmented objects as vector graphics.
Image datasets are generally too big to be served to the client en bloc. Therefore, datasets are tiled up and dynamically streamed from the server for display. The client application only requests the subset of raster and vector tiles relevant for the current view and renders and caches them efficiently on the local graphics card via `WebGL <https://www.khronos.org/webgl/>`_. This results in a smooth user experience with reduced bandwidth.
Key features are support for brightfield and fluorescence mode, toggling and colorization of different channels and objects as well as instant intensity scaling and opacity adaptation for individual channels and object types, respectively.

.. TODO: screenshot

.. _data-anlysis-tools:

Data analysis tools
^^^^^^^^^^^^^^^^^^^

In addition to visualization, the viewer provides plugins for visually-assisted data analysis and machine learning. These tools allow users to interact with objects on the *map*, query information about them and subject them to to further analysis. Users can, for example, colorcode objects according to precomputed feature values and on the fly computed classification labels or visualize objects in multivariate feature space alongside their spatial *map* represenation.

.. TODO: screenshot

.. _workflow-manager:

Workflow Manager
----------------

The zoomable multi-scale representation requires overview images in form of tiled `pyramids <https://en.wikipedia.org/wiki/Pyramid_(image_processing)>`_. In addition, objects of interest need to be computationally identified in the images and quantitatively assessed by means of image segmentation and feature extraction, respectively, before they can be displayed on the *map* and used for further analyis.

Serveral interdependent processing steps are usually required to get from the raw images as outputted by the microscope to the final single-cell feature matrix. `TissueMAPS` provides a user-friendly interface to setup automated image analysis workflows, submit them to a cluster for distributed processing, monitor the status of submitted computational jobs and report results and statistics upon completion.

.. TODO: screenshot


.. TODO: screenshot

.. _distributed-image-processing:

Distributed image processing
============================

An image processing workflow represents a series of *steps*, each of which comprises a set of computational *jobs* that get distributed across available compute resources for parallel processing. Functionally related *steps* are further grouped into abstract *stages*. The entire workflow can be submitted for processing or individual *stages* can be submitted one after the other. Since results of each *step* are persisted on disk, workflows can further be resubmitted from any given *stage*.

The :mod:`tmlib.workflow` package provides functionality for generating and managing distributed image processing workflows. Each of the steps is implemented as a subpackage of :mod:`tmlib.workflow` and represents a parallel computational task collection that can also be invoked separately via the command line.

The following "canonical" `TissueMAPS` workflow for automated analysis of multi-wellplate screens is used here for illustration. To meet specific user requirements, custom workflows can be easily created, either by modifying or extending existing workflows or by creating new ones from scratch.

.. _canonical-workflow:

Canonical workflow
------------------


.. figure:: ./_static/canonical_workflow.png
   :width: 75%
   :align: left

   Stages of the canonical workflow.

   "Upload" and "Download" are not actual stages of the image processing *workflow* and handled separately.


Image conversion
^^^^^^^^^^^^^^^^

Image pixel data and metadata are extracted from heterogeneous microscopy file formats and stored in a consistent way, which is optimized for efficient downstream parallel processing.

Steps:

- :doc:`metaextract <tmlib.workflow.metaextract>`: Extraction of metadata

- :doc:`metaconfig <tmlib.workflow.metaconfig>`: Configuration of metadata

- :doc:`imextract <tmlib.workflow.imextract>`: Extraction of image data

Image preprocessing
^^^^^^^^^^^^^^^^^^^

Global statistics are computed across all images and persisted for use by subsequent processing steps.

Steps:

- :doc:`corilla <tmlib.workflow.corilla>`: Calculation of illumination statistics

Pyramid creation
^^^^^^^^^^^^^^^^

Image pyramids are created for interactive visualization. The user can optionally apply illumination statistics generated in the previous stage to correct images for illumination artifacts.

Steps:

- :doc:`illuminati <tmlib.workflow.illuminati>`: Image pyramid creation

Image analysis
^^^^^^^^^^^^^^

Images are subjected to image segmentation and feature extraction. `Jterator` provides an interace to build and run custom image analysis pipelines, which can be constructed from available modules. These modules are available through the :mod:`jtmodules` package hosted by the `JtModules <https://github.com/TissueMAPS/JtModules>`_ repository.

Steps:

- :doc:`jterator <tmlib.workflow.jterator>`: Image segmentation and feature extraction

The `jterator` workflow step is special in the sense that it provides an additional logic of constructing pipelines. The `jterator` pipeline runs in memory on individual compute nodes, each of which processes a subset (batch) of images.

.. TODO: screenshot of jtui

.. _machine-learning-tools:

Machine learning tools
======================

The :mod:`tmlib.tools` package provides an extendible plug-in framework for machine learning tools.
These tools enable users to perfom explanatory data analysis directly on the map in an interactive and responsive manner and thereby combine quantitative, statistical analysis with human visual pattern recognitition. Each tool has a client and a server side representation. The client provides an interface for the user and sends tool requests issued by the user to the server. The server handles requests (a computation and/or database query) and responds with a tool-specific result that the client knows how to interpret and visualize. Tool request are handled asynchronously and submitted to the cluster for processing.

What can these tools be used for? Let's consider the following example: After extracting a multitude of features for segmented objects , you may be interested in the distribution of feature values and identification of outliers (interesting phenotypes or artifacts). In addition, you may want to visually compare the results of your analysis with the images from which the features were extracted. To this end, you may download the dataset, load it into R and generate some fancy gg-plots. Once you have found an interesting pattern in data, you would have to go through painful rounds of indexing to find the pixels corresponding to your data points of interest (segmented objects) back in the original images. `TissueMAPS` tools provide a framework to perform such explorative analysis via the user interface in an automated way that does not require any programming.

