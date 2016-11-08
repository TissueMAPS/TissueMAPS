***************
Developer guide
***************


.. _frontend:

Frontend
========

.. _architecture:

Architecture
------------

The web frontend of TissueMAPS is largely based on the framework `AngularJS <https://angularjs.org/>`_.

Classes and functions encapsulating core application logic and that are therefore not UI-specific are separated from the UI-specifc code.
Code comprising core application logic is located in the subdirectory ``core`` and the other directories are reserved for code handling views, user input, as well as AngularJS-related things.
Several server-side resources like the *Experiment* also have a client-side representation.
However, it is important to note that these concepts are not exactly the same.
A client-side experiment is *constructed* from a serialized server-side experiment but can also have other properties that is only interesting to code dealing with the user interface.


.. _data-access-objects:

Data access objects (DAO)
-------------------------

.. _dialogs:

Whenever a class in TissueMAPS wants to access a resource from the server, the call has to go through a model-specific *data access object (DAO)*.
These objects issue HTTP-requests and handle the deserialization process when contructing actual model class instances from JSON objects.

Dialogs
-------

To display messages to the user by means of dialogs (popup windows), TissueMAPS provides a service called ``dialogService``.
For example, to inform the user that some request has been performed successfully, this service can be used like this::

    dialogService.info('Task XY has been performed successfully')

Similar utility methods exist for error or warning messages.

Errors that result because of some server-side issue (such as authorization failures or not found resources) are caught by an ``errorInterceptor`` and automatically displayed to the user. Thus, manually handling such errors is not necessary.


.. _viewer:

Viewer
------

The main class of the TissueMAPS interface is the ``Viewer`` class. The viewer is in charge of visualizing an experiment and to handle related resources such as mapobjects and tools with which the experiment can be analyzed.

The actual visualization of the microscopy images is done with an extended version of `OpenLayers <https://openlayers.org>`_ that allows WebGL-powered rendering of tiled images and vector data, as well as additive blending of images.
The interface to OpenLayers is hidden within several wrapper classes such as ``ImageTileLayer`` and ``VectorTileLayer``.
Ultimately, whenever the user scrolls the map, OpenLayers will prompt the underlying layer objects to perform a GET request to the tile server to get a slice of the pyramid image or a collection of vectoral data (for example cell outlines).
Analoguous to these layer classes, the ``Viewport`` class is a wrapper around an OpenLayers ``Map`` object and is used within TissueMAPS to add and remove layer objects.


.. _data-analysis-tools:

Data analysis tools
-------------------

The TissueMAPS interface uses a plugin mechanism for data analysis tools.
This mechanism ensures that each implemented tool can be selected from the toolbar and that results returned from the server are interpreted correctly.
To make use of this plugin mechanism, the code for an existing or new tool has to follow some conventions.

A tool is located under ``src/tools/{ToolName}`` and should provide a AngularJS controller named ``{ToolNameCtrl}``.
When clicking on a tool button in the toolbar, TissueMAPS will create an instance of this controller and link it to a tool window-specific ``$scope``.
This tool window will further be populated with a custom template content.

.. TODO: Where is it defined again which tool has which template? It seems this has changed. Is it supplied by the server?

Templates can make use of several pre-defined widgets.
For example, the following tag will insert a widget with which the desired mapobject type can be selected::

    <tm-mapobject-type-widget></tm-mapobject-type-widget></p>


Another widget can be used to select a specific feature::

    <tm-feature-selection-widget
      selected-mapobject-type="mapobjectTypeWidget.selectedType">
    </tm-feature-selection-widget>

Implementations of existing tools provide a good idea of how to implement a new tool.

.. _backend:

Backend
=======

.. _workflows:

Workflows
---------

.. _data-analysis-tools:

Data analysis tools
-------------------

.. _jterator-modules:

Jterator modules
----------------

`TissueMAPS` provides with :mod:`jterator <tmlib.workflow.jterator>` a **cross-language pipeline engine** for scientific computing and image analysis. The program uses `Python <https://www.python.org/>`_ as a glue language, but can plug in **modules** written in different languages. It makes use of easily human readable and modifiable `YAML <http://yaml.org/>`_ files to define pipeline logic and module input/output.

Python was chosen as programming language because it represents a good trade-off between development time and performance. The language is relatively easy to learn and its interpreted nature facilitates scripting and testing. The powerful `NumPy <http://www.numpy.org/>`_ package provides an great framework for n-dimensional array operations. In addition, there are numerous established C/C++ image processing libraries with Python bindings that use `NumPy arrays <http://docs.scipy.org/doc/numpy/reference/arrays.html>`_ as data container:

- `ITK <http://www.simpleitk.org/>`_
- `openCV <http://opencv.org/>`_
- `mahotas <http://mahotas.readthedocs.org/en/latest/index.html>`_

This makes it easy to combine algorithms implemented in different libraries into an image analysis workflow. In addition to Python, `jterator` pipelines can integrate modules written in other programming languages frequently used for scientific computing:

- Matlab: `matlab_wrapper <https://github.com/mrkrd/matlab_wrapper>`_
- R: `rpy2 <http://rpy.sourceforge.net/>`_
- Julia: `pyjulia <https://github.com/JuliaLang/pyjulia>`_

.. _jterator-main-ideas:

Main ideas
^^^^^^^^^^

- **Simple development and testing**: A module is simply a file that defines a function for the main entry point and creates a namespace.
- **Short list of dependencies**: A module only requires the `NumPy <http://www.numpy.org/>`_ package.
- **Independence of processing steps**: Module arguments are either `NumPy` arrays, scalars (integer/floating point numbers, strings or booleans), or a sequence of scalars. Modules don't produce any side effects. They are unit testable.
- **Strict separation of GUI handling and actual processing**: Modules don't interact with a GUI or file system. Their `main` function receives images in form of arrays as input arguments and returns images in form of arrays. They can optionally generate and return a JSON representation of a figure which can be embedded in a website for interactive visualization.
- **Cross-language compatibility**: Restriction of module input/output to `NumPy` arrays and build-in Python types to facilitate interfaces to other languages.


.. _jterator-pipeline:

Pipeline
^^^^^^^^

A *pipeline* is a sequence of connected *modules* that collectively represents a computational task (somewhat similar to a UNIX-world pipeline), i.e. a unit of execution that runs in memory on a single compute unit.
Order of *modules* and pipeline input are defined in a *.pipe* YAML :ref:`pipeline descriptor file <jterator-pipeline-descriptor-file>`. Input/output settings for each module are provided by additional *.handles* YAML :ref:`module I/O descriptor files <jterator-module-descriptor-files>`.


.. _jterator-pipeline-descriptor-file:

Pipeline descriptor file
************************

Here is an example of a *.pipe.yaml* YAML descriptor file:

.. code-block:: yaml

    description: An example pipeline that does nothing.

    version: '0.0.1'

    input:

        channels:
          - name: channel1
            correct: true
          - name: channel2
            correct: true

    pipeline:

        -   source: python_module.py
            handles: handles/my_python_module.handles.yaml
            active: true

        -   source: r_module.r
            handles: handles/my_r_module.handles.yaml
            active: true

        -   source: matlab_module.m
            handles: handles/my_m_module.handles.yaml
            active: true


The **pipeline** section is an array of included modules. Module ``handles`` files can in principle reside at any location and the path to the files has to be provided. This path can either be absolute or relative to the project directory (as in the example above). Module ``source`` files must reside within the language-specific *jtmodules* package, since they should be importable. Only the file basename must be provided. Modules are run or skipped depending on the value of ``active``. Alternatively, modules can of course also be inactivated by commenting them out; however, this is incompatible with the user interface.

All ``channels`` specified in the **input** section will be loaded by the program and the corresponding images made available to modules in the pipeline. Images will optionally be corrected for illumination artifacts depending on the value of ``correct``.

.. _jterator-modules:

Modules
^^^^^^^

Modules are the actual executable code in the pipeline. A module is file that defines a ``main()`` function, which serves as the main entry point for the program. Modules must be free of side effects, in particular they don't write to disk. This will be enforced by `jtertor` by calling the module function in a `sandbox <http://stackoverflow.com/questions/2126174/what-is-sandboxing>`_.
Special modules are available for storing data generated within a pipeline, such as segmentation results and features extracted for the segmented objects.

Python `modules <https://docs.python.org/2/tutorial/modules.html>`_ encapsulate code and provide a separate scope and namespace. Conceptually they are classes with attributes (constants) and static methods (functions). For compatibility we use a similar implementation for non-Python languages to provide the user a similar interface across different languages (Matlab, R, ...).

To this end, each *module* must define a ``VERSION`` constant and a ``main()`` function. The `main` function serves as the main entry point and will be called by `jterator` when executed as part of a pipeline. You can add additional "private" functions/methods to the module. Note, however, that code, which is intended for reuse across modules, should be rather imported from a separate library, such as `jtlibrary <https://github.com/TissueMAPS/JtLibrary>`_ or any other installable package.

Shown here are minimalistic examples of modules in different languages. They don't do much, execpt returning one of the input arguments.

.. _jterator-module-python-example:

Python example
**************

.. code-block:: python

    import collections
    import jtlib

    VERSION = '0.0.1'

    Output = collections.namedtuple('Output', ['output_image', 'figure'])

    def main(input_image, plot=False):

        if plot:
            figure = jtlib.plotting.create_figure()
        else:
            figure = ""

        return Output(input_image, figure)


The module named ``python_module`` (residing in a file called ``python_module.py``) can be imported and called as follows:

.. code-block:: python

    import numpy as np
    import jtmodules.python_module

    img = np.zeros((10,10))
    jtmodules.python_module.main(img)

.. note:: The return type of ``main()`` must be `namedtuple <https://docs.python.org/2/library/collections.html#collections.namedtuple>`_. Instances of this type behave like tuple objects, which can be indexed and are iterable. In addition, however, fields are accessible via attribute lookup:

    .. code-block:: python

       import numpy as np
       from jtmodules.python_module import Output

       output = Output(np.zeros((5, 5)), "")

       # Objects are iterable
       for out in output:
           print out

       # Object fields can be indexed and accessed via attribute lookup
       print output[0]
       print output.output_image

.. _jterator-module-matlab-example:

Matlab example
**************

To get the same interface and namespace in *Matlab*, we need to implement the ``main()`` function as a static method of class ``matlab_module``.

.. code-block:: matlab

    import jtlib.*;

    classdef matlab_module

        properties (Constant)

            VERSION = '0.0.1'

        end

        methods (Static)

            function [output_image, figure] = main(input_image, plot)

                if nargin < 2
                    plot = false;
                end

                if plot
                    figure = jtlib.plotting.create_figure();
                else
                    figure = '';
                end

                output_image = input_image;

            end

        end
    end


Thereby, the module named ``matlab_module`` (residing in a file called ``matlab_module.m``) can be imported and called the same way as Python modules:

.. code-block:: matlab

    import jtmodules.matlab_module;

    img = (10, 10);
    jtmodules.matlab_module.main(img)


.. note:: Matlab functions must return output arguments using the ``[]`` notation.

.. warning:: Matlab class `struct` is not supported for input arguments or return values!

.. _jterator-module-r-example:

R example
*********

To implement the same interface in *R*, we have to get a bit more inventive, since *R* is is not a propper programming language (Ups!).

.. code-block:: r

    library(jtlib)

    r_module <- new.env()

    r_module$VERSION <- '0.0.1'

    r_module$main <- function(input_image, plot=FALSE){

        output <- list()
        output[['output_image']] <- input_image

        if (plot) {
            output[['figure']] <- jtlib::plotting.create_figure()
        } else {
            output[['figure']] <- ''
        }

        return(output)
    }

The module named ``r_module`` (residing in a file called ``r_module.r``) can now be imported and called using ``$`` as namespace separator:

.. code-block:: r

    library(jtmodules)

    img <- matrix(0, 10, 10)
    jtmodules::r_module$main(img)


.. note:: The return value of ``main()`` in *R* must be a `list` with named members.


.. _jterator-module-descriptor-files:

Module descriptor files
^^^^^^^^^^^^^^^^^^^^^^^

Input and output of modules is described in module-specific *handles* files:

.. code-block:: yaml

    version: 0.0.1

    input:

        - name: string_example
          type: Character
          value: mystring

        - name: integer_example
          type: Numeric
          value: 1
          options:
            - 1
            - 2

        - name: piped_image_input_example
          type: IntensityImage
          key: a.unique.string

        - name: array_example
          type: Sequence
          value:
            - 2.3
            - 1.7
            - 4.6

        - name: boolean_example
          type: Boolean
          value: true

        - name: plot
          type: Plot
          value: false

    output:

        - name: piped_image_output_example
          type: LabelImage
          key: another.unique.string

        - name: figure
          type: Figure


Each :class:`handle <tmlib.workflow.jterator.handles.Handle>` item in the **input** section describes an argument that is passed to the ``main()`` function of the module. Each item in the **output** section describes an argument of the module-specifig output object (return value), which should be returned by the ``main()`` function.

The *handle* ``type`` descriped in the YAML file is mirrored by a Python class, which asserts data types and handles input/output. Constant input arguments have a ``value`` key, which represents the actual argument. Images can be piped between modules and the corresponding input arguments have a ``key`` key. It serves as a lookup for the actual value, i.e. the pixels array, which is stored an an in-memory key-value store. The value of ``key`` in the YAML description must be a hashable and therefore unique across the entire pipeline. Since names of *.handles* files are unique, best practice is to use the handle filename as a namespace and combine them with the name of the output *handle* to create a unique hashable identifier (for the above Python example the key would resolve to `"my_py_module.output_image"`).

The following *handle* types are implemented:

* **Constant** input *handle* types: parameters that specify the actual argument value (derived from :class:`InputHandle <tmlib.workflow.jterator.handles.InputHandle>`)
    - :class:`Numeric <tmlib.workflow.jterator.handles.Numeric>`: number (``int`` or ``float``)
    - :class:`Character <tmlib.workflow.jterator.handles.Character>`: string (``basestring``)
    - :class:`Boolean <tmlib.workflow.jterator.handles.Boolean>`: boolean (``bool``)
    - :class:`Sequence <tmlib.workflow.jterator.handles.Sequence>`: atomic array (``list`` of ``int`` or ``float`` or ``basestring`` or ``bool``)
    - :class:`Plot <tmlib.workflow.jterator.handles.Plot>`: boolean (``bool``)

* **Pipe** input and output *handle* types: parameters that specify a "key" to retrieve the actual argument value (derived from :class:`PipeHandle <tmlib.workflow.jterator.handles.PipeHandle>`)
    - :class:`IntensityImage <tmlib.workflow.jterator.handles.IntensityImage>`: grayscale image  with 8-bit or 16-bit unsigned integer data type (``numpy.uint8`` or ``numpy.uint16``)
    - :class:`LabelImage <tmlib.workflow.jterator.handles.LabelImage>`: labeled image with 32-bit integer data type (``numpy.int32``)
    - :class:`BinaryImage <tmlib.workflow.jterator.handles.BinaryImage>`: binary image with boolean data type (``numpy.bool``)
    - :class:`SegmentedObjects <tmlib.workflow.jterator.handles.SegmentedObjects>`: subtype of :class:`LabelImage <tmlib.workflow.jterator.handles.LabelImage>`, with additional methods for registering connected components in the image as objects, which can subsequently be used by measurement modules to extract features for the objects

* **Measurement** output *handle* type: parameters that specify ``object_ref`` to reference the provided value to an instance of :class:`SegmentedObjects <tmlib.workflow.jterator.handles.SegmentedObjects>` and optionally ``channel_ref`` to also reference the value to an instance of :class:`IntensityImage <tmlib.workflow.jterator.handles.IntensityImage>` (derived from :class:`OutputHandle <tmlib.workflow.jterator.handles.OutputHandle>`)
    - :class:`Measurement <tmlib.workflow.jterator.handles.Measurement>`: array of multidimensional matrices (one per time point), where columns are features and rows are segmented objects (``list`` of ``pandas.DataFrame`` with data type ``numpy.float``)

* **Figure** output *handle* type: parameters that register the provided value as a figure (derived from :class:`OutputHandle <tmlib.workflow.jterator.handles.OutputHandle>`)
    - :class:`Figure <tmlib.workflow.jterator.handles.Figure>`: JSON serialized figure (``basestring``, see `plotly JSON schema <http://help.plot.ly/json-chart-schema/>`_)

Values of `SegmentedObjects`, `Measurement`, and `Figure` handles are automatically persisted on disk.
To this end, segmented objects need to be registered via the :mod:`register_objects <jtmodules.register_objects>` module.

.. note:: Values of `SegmentedObjects` and `Measurement` will become available in the viewer as *objects* and *features*, respectively, and can be used by data analysis *tools*.


The ``Plot`` input and ``Figure`` output handle types are used to implement plotting functionality. The program will automatically set ``plot`` to ``false`` for running in headless mode on the cluster.

.. warning:: To implement plotting use the provided :class:`Plot <tmlib.workflow.jterator.handles.Plot>` and :class:`Figure <tmlib.workflow.jterator.handles.Figure>` *handle* types. Otherwise, *headless* mode can't be enforced.


.. _jterator-code-structure:

Code structure
^^^^^^^^^^^^^^

Modules should be light weight wrappers and mainly concerned with handling input and returning output in the expected format (and optionally the creation of a figure). Optimally, the actual image processing gets delegated to libraries to facilitate reuse of code by other modules. Importing modules in other modules is discouraged. You can use external libraries or implement custom solutions in the provided :mod:`jtlibrary` package (available for each of the implemented languages).


.. _jterator-naming-conventions:

Naming conventions
^^^^^^^^^^^^^^^^^^

Since Jterator is written in Python, we recommend following `PEP 0008 <https://www.python.org/dev/peps/pep-0008/>`_ style guide for module and function names.
Therefore, we use short *all-lowercase* names for modules with *underscores* separating words if necessary, e.g. ``modulename`` or ``long_module_name``. See `naming conventions <https://www.python.org/dev/peps/pep-0008/#prescriptive-naming-conventions>`_.

.. _jterator-coding-style:

Coding style
^^^^^^^^^^^^

For Python, we encourage following `PEP 0008 <https://www.python.org/dev/peps/pep-0008/>`_ style guide. For Matlab and R we recommend following Google's style guidelines, see `Matlab style guide <https://sites.google.com/site/matlabstyleguidelines/>`_ (based on Richard Johnson's `MATLAB Programming Style Guidelines <http://www.datatool.com/downloads/matlab_style_guidelines.pdf>`_) and `R style guide <http://www.datatool.com/downloads/matlab_style_guidelines.pdf>`_.


.. _jterator-figures:

Figures
^^^^^^^

The plotting library `plotly <https://plot.ly/api/>`_ is used to generate interactive plots for visualization of module results in the web-based user interface. The advantage of this library is that is has a uniform API and generates identical outputs across different languages (Python, Matlab, R, Julia). Each module creates only one figure. If you have the feeling that you need more than one figure, it's an indication that you should break down your code into multiple modules.


.. _jterator-documentation:

Documentation
^^^^^^^^^^^^^

We use `sphinx <http://www.sphinx-doc.org/en/stable/>`_ with the `numpydoc <https://github.com/numpy/numpydoc/>`_ extension to auto-generate module documentation. Each module must have a docstring that describes its functionality and purpuse. In addition, a dosctring must be provided for the ``main()`` function that describes input parameters and return values. Please make yourself familiar with the `NumPy style <https://github.com/numpy/numpy/blob/master/doc/HOWTO_DOCUMENT.rst.txt>`_ and follow the `PEP 0257 docstring conventions <https://www.python.org/dev/peps/pep-0257/>`_ to ensure that the documentation for your module will be build correctly.

.. _jterator-tests:

Tests
^^^^^

.. TODO:


