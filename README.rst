.. _introduction:

Introduction
============

Jterator is a **cross-language pipeline engine** for scientific computing and image analysis.

The program itself is written in `Python <https://www.python.org/>`_, but it can process data across different languages. It makes use of easily human readable and modifiable `YAML <http://yaml.org/>`_ files to define pipeline logic and module input/output.

Python was chosen as programming language because it represents a good trade-off between development time and performance. In combination with the `NumPy <http://www.numpy.org/>`_ package, it provides an ideal framework for scientific computing and image analysis. In addition, there are numerous powerful image processing libraries with Python bindings that use NumPy arrays as data container:   

- `scikit-image <http://scikit-image.org/docs/dev/auto_examples/>`_   
- `simpleITK <http://www.simpleitk.org/>`_
- `openCV <http://opencv.org/>`_
- `mahotas <http://mahotas.readthedocs.org/en/latest/index.html>`_

This makes it easy to combine algorithms from different libraries into an image analysis workflow. Jterator further provides integration of code written in other programming languages frequently used for image processing and statistical data analysis, such as   

- Matlab: `matlab_wrapper <https://github.com/mrkrd/matlab_wrapper>`_ 
- R: `rpy2 <http://rpy.sourceforge.net/>`_
- Java: `Py4J <https://www.py4j.org/>`_
.. - Julia: `pyjulia <https://github.com/JuliaLang/pyjulia>`_

.. _main-ideas:

Main ideas
==========

- *Simple module development and testing*: A module represents a file that contains a function with the same name as the file.
- *Short list of dependencies*: Writing a module only requires the `NumPy <http://www.numpy.org/>`_ package.
- *Independence of individual processing steps*: Module arguments are either `NumPy` arrays, scalars (integer and floating point numbers and strings), or a sequence of scalars. Modules don't perform IO. They are therefore unit testable.
- *Separation of GUI handling from the actual image processing*: Modules don't interact with a GUI. They can, however, generate and return a JSON representation of a figure which can be visualized in a browser.
- *Cross-language compatibility*: Restricting module input/output to `NumPy` arrays and build-in Python types facilitates interfaces to other languages.


.. _pipeline:

Pipeline
========

A pipeline is a sequence of connected modules that collectively represents a computational task, i.e. a unit of execution that runs on a single machine.
The sequence and structure of your pipeline is defined in a *pipe* YAML `pipeline descriptor file`_. The input/output settings for each module are provided by additional *handles* YAML `module IO descriptor files`_.


.. _pipeline-descriptor-file:

Pipeline descriptor file
------------------------

Jterator allows only very simplistic types of work-flow -  *pipeline* (somewhat similar to a UNIX-world pipeline). 

Example of a *.pipe.yaml* YAML descriptor file:

.. code-block:: yaml

    description: An example project that does nothing.

    input:

        channels:
          - name: myExampleLayer1
            correct: true
          - name: myExampleLayer2
            correct: true

    pipeline:

        -   source: my_python_module.py
            handles: handles/my_python_module.handle.yml
            active: true

        -   source: my_r_module.r
            handles: handles/my_r_module.handle.yml
            active: true

        -   source: my_m_module.m
            handles: handles/my_m_module.handle.yml
            active: true


Handle files can in principle reside at any location. The path to the files has to be provided in the pipeline descriptor file. This path can be absolute or relative to the project directory (as in the example above). Module files must reside within the repository. The path to the local copy of the repository can either be provided by setting the ``JTLIB`` environment variable or by setting a value for the ``lib`` key within the pipeline descriptor file.  
All *channels* and *mapobject_types* specified in **input** will be loaded by the program and the corresponding images made available to modules in the pipeline.

.. _modules:

Modules
=======

Modules are the actual executable code in the pipeline. Each module is simply a file that defines a function with the same name as the file.

.. _data:

Data
----

Modules don't perform disk IO! Special modules are available for storing data generated within a pipeline, such as segmentation results and features extracted for the segmented objects.


.. _figures:

Figures
-------

Figures are generated using the `plotly <https://plot.ly/api/>`_ library and returned by modules as JSON strings.


.. _module-expamples:

Module examples
---------------

Shown here are minimalistic examples of modules that simply return their input implemented in different languages.
A Python module encapsulates code and provides a separate scope and a namespace. They can be regarded as a class with attributes (constants) and static methods (functions). For compatibility we use a similar implementation for non-Python languages (Matlab, R, ...).
Each *module* must define a constant ``VERSION`` and a function ``main``. The ``main`` function is the main entry point of the module and will be called when executed in the pipeline. You can add additional "private" methods to the module. Note, however, that code that should be reused across modules, should be placed in the `jtlib <https://github.com/TissueMAPS/JtLibrary>`_ package or any other installable package.

**Python example**:     

.. code:: python

    import jtlib
    
    VERSION = '0.0.1'

    def main(input_image, plot=False):

        output = dict()
        output['output_image'] = input_image

        if plot:
            output['figure'] = jtlib.plotting.create_figure()
        else:
            output['figure'] = ""

        return output

The module named ``my_py_module`` (residing in a file called ``my_py_module.py``) can be imported and called as follows:

.. code:: python
    
    import numpy as np
    import jtmodules.my_py_module
    
    img = np.zeros((10,10))
    jtmodules.my_py_module.main(img)

.. Note::

    The return value in Python must have type ``dict``.

**Matlab example**:     

.. code-block:: matlab

    import jtlib.*;
    
    classdef my_m_module
    
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
    
    
The module named ``my_m_module`` (residing in a file called ``my_m_module.m``) can be imported and called as follows:

.. code:: matlab
    
    import jtmodules.my_m_module;
    
    img = (10, 10);
    jtlib.modules.my_m_module.main(img)


.. Note::

    Matlab functions must return output arguments using the ``[]`` notation.

.. Warning::

    Class `struct` is not supported for arguments or return values!

**R example**:

.. code-block:: R

    library(jtlib)
    
    my_r_module <- new.env()

    my_r_module$VERSION <- '0.0.1'
    
    my_r_module$main <- function(input_image, plot=FALSE){

        output <- list()
        output[['output_image']] <- input_image

        if (plot) {
            output[['figure']] <- jtlib::plotting.create_figure()
        } else {
            output[['figure']] <- ''
        }

        return(output)
    }
    
The module named ``my_r_module`` (residing in a file called ``my_r_module.r``) can be imported and called as follows:

.. code:: r
    
    library(jtmodules)
    
    img <- matrix(0, 10, 10)
    jtmodules::my_r_module$main(img)


.. Note::
    
    The return value in R must have type `list` and the list must have named members.


.. _module_descriptor-files:

Module descriptor files
-----------------------

Input and output of modules is described in module-specific *handles* files:        

.. code-block:: yaml

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

        - name: pipeline_input_example
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

        - name: pipeline_output_example
          type: LabelImage
          key: another.unique.string

        - name: figure
          type: Figure


Each item (*handle*) in the array of inputs describes an argument that is passed to the module function and each item in the array of outputs describes a key-value pair of the mapping that should be returned by the function.

The *type* of a handle descriped in the YAML file is mirrored by a Python class. Constant input arguments have a "value" key, which represents the actual argument. Images can be piped between modules and have a "key" key, which serves as a lookup for the actual value, i.e. the image, in an in-memory key-value store. The value for that YAML key must be a hashable, i.e. a string that's unique within the pipeline. Since the names of handles files are unique, best practice is to use handle filenames as a namespace and combine them with the name of the output handle to create a unique hashable identifier (e.g. for the above Python example the key would be `"my_python_module.output_image"`).

The following handle *types* are available:

* Constant input handles: parameters that specify the actual argument value
    - **Numeric**: number (``int`` or ``float``)
    - **Character**: string (``basestring``)
    - **Boolean**: boolean (``bool``)
    - **Sequence**: array (``list`` of `int` or ``float`` or ``basestring``)
    - **Plot**: boolean (``bool``)
        
* Pipe handles (input and output): parameters that specify a "key" to retrieve the actual argument value (``numpy.ndarray``)
    - **IntensityImage**: grayscale image  with 8-bit or 16-bit unsigned integer data type (```numpy.uint8`` or ``numpy.uint16``)
    - **LabelImage**: labeled image with 32-bit integer data type (``numpy.int32``)
    - **BinaryImage**: binary image with boolean data type (``numpy.bool``)
    - **SegmentedObjects**: same as *LabelImage*, but automatically registers connected components in the image as segmented objects, which can subsequently be used by measurement modules to extract features for the objects
        
* Measurement output handles: parameters that specify an ``"object_ref"`` to reference the provided value to an instance of ``SegmentedObjects`` (and optionally a ``"channel_ref"`` to also reference the value to an instance of ``IntensityImage`` representing a "channel")
    - **Measurement**: measurements as a multidimensional matrix per time point, where columns are features and rows are segmented objects (``list`` of ``pandas.DataFrame`` with data type ``numpy.float``)

* Figure output handles: parameters that register the provided value as a figure
    - **Figure**: serialized figure (``basestring``), see `plotly JSON schema <http://help.plot.ly/json-chart-schema/>`_.
        
The values of ``SegmentedObjects``, ``Measurement``, and ``Figure`` handles are automatically persisted - either on disk or in the database. The values of ``SegmentedObjects`` are available in the *TissueMAPS* viewer as *objects* and drawn on the map and those of ``Measurement`` as *"features"*, which can be used by the data analysis *tools*.
        


The ``Plot`` input handle type and ``Figure`` output handle type are used to implement plotting functionality. The program will set ``plot`` to ``false`` when running in headless mode on the cluster.

Segmented objects and extracted featuresneed to be registered in the database. This is automatically handled by jterator and achieved via the ``SegmentedObjects`` and ``Measurement`` handle types. To be able to store measurement for a given mapobject type, objects need to be registered via the `register_objects.py` module.


.. _developer-documentation:

Developer documentation
=======================

Modules should be light weight wrappers and the code mainly concerned with input/output handling and (optionally) the generation of a figure. The actual image processing should be delegated to libraries. To this end, one can make use of external libraries or implement custom solutions in the `jtlib` package (available for each of the implemented languages). This makes it also easier to reuse code across modules.


.. _naming-conventions:

Naming conventions
------------------

Since Jterator is written in Python, we recommend following `PEP 0008 <https://www.python.org/dev/peps/pep-0008/>`_ style guide for module and function names.
Therefore, we use short *all-lowercase* names for Jterator modules with *underscores* separating words if necessary, e.g. ``modulename`` or ``long_module_name``. See `naming conventions <https://www.python.org/dev/peps/pep-0008/#prescriptive-naming-conventions>`_.
In the case of Python, a jterator module is simply a Python module that contains a function with the same name as the module.
This approach also works for `Matlab function files <http://ch.mathworks.com/help/matlab/matlab_prog/create-functions-in-files.html>`_ as well as `R scripts <https://cran.r-project.org/doc/contrib/Lemon-kickstart/kr_scrpt.html>`_.


.. _coding-style:

Coding style
------------

For Python, we encourage following `PEP 0008 Python style guide <https://www.python.org/dev/peps/pep-0008/>`_. For Matlab and R we recommend following Google's style guidelines, see `Matlab style guide <https://sites.google.com/site/matlabstyleguidelines/>`_ (based on Richard Johnson's `MATLAB Programming Style Guidelines <http://www.datatool.com/downloads/matlab_style_guidelines.pdf>`_) and `R style guide <http://www.datatool.com/downloads/matlab_style_guidelines.pdf>`_.


.. _figures:

Figures
-------

The plotting library `plotly <https://plot.ly/api/>`_ is used to generate interactive plots for visualization of module results in the web-based user interface. The advantage of this library is that is has a uniform API and generates identical outputs across different languages (Python, Matlab, R, Julia). Each module creates only one figure. If you have the feeling that you need more than one figure, it's an indication that you should break down your code into multiple modules.


.. _documentation:

Documentation
-------------

We use `sphinx <http://www.sphinx-doc.org/en/stable/>`_ with the `numpydoc <https://github.com/numpy/numpydoc/>`_ extension to auto-generate the documentation of modules. Each module should have a docstring that describes the function, input parameters, and outputs. Please make yourself familiar with the `NumPy style <https://github.com/numpy/numpy/blob/master/doc/HOWTO_DOCUMENT.rst.txt>`_ and follow the `PEP 0257 docstring conventions <https://www.python.org/dev/peps/pep-0257/>`_ to ensure that the documentation for your module will be displayed correctly.
