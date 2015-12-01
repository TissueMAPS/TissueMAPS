.. _introduction:

************
Introduction
************

Jterator is a **cross-language pipeline engine** for scientific computing and image analysis.

It is designed to be flexible and customizable, while at the same time being easy to use. The program itself is written in `Python <https://www.python.org/>`_, but it can process data across different languages. It makes use of easily readable and modifiable `YAML <http://yaml.org/>`_ files to define project layout, pipeline logic, and module input/output and stores output data in `HDF5 <https://www.hdfgroup.org/HDF5/>`_ files. It comes with a **command line interface** as well as a **web-based user interface**.

Python was chosen as programming language because it represents a good trade-off between development time and performance. In addition, it provides access to numerous powerful image processing libraries, such as   

- `scikit-image <http://scikit-image.org/docs/dev/auto_examples/>`_   
- `simpleITK <http://www.simpleitk.org/>`_
- `openCV <http://opencv.org/>`_
- `mahotas <http://mahotas.readthedocs.org/en/latest/index.html>`_  

Jterator pipes data as `numpy <http://www.numpy.org/>`_ arrays and allows integration of code written in other high-level programming languages frequently used for image processing and statistical data analysis, such as   

- Matlab: `matlab_wrapper <https://github.com/mrkrd/matlab_wrapper>`_ 
- R: `rpy2 <http://rpy.sourceforge.net/>`_
- Julia: `pyjulia <https://github.com/JuliaLang/pyjulia>`_

This can be useful to combine Jterator modules with existing code without having to rewrite everything in Python.

.. _main-ideas:

The main ideas
==============

- rapid development and testing of new workflows
- clear separation of GUI handling from actual processing
- short list of (difficult to build) dependencies
- cross-language compatibility

.. _project:

Project
=======

A Jterator project corresponds to a folder on disk with the following layout:

* **handles** folder contains all the YAML *.handles.yml* module descriptor files, which are passed as STDIN stream to *modules*. This folder is created when you set up your pipeline, either via user interface or via the command line using the ``jt create`` command.
* **data** folder contains all the *.data.h5* HDF5 output files. Jterator will automatically create this folder in your project directory.
- **figures** folder contains all the figure files. These files may either be *HTML* documents or *PNG* image files.        
* **logs** folder contains all the output from STDOUT and STERR streams, obtained for each executable that has been executed in the pipeline. The logging level can be controlled via the ``-v`` or ``--verbosity`` argument.

The actual module files can reside in the project directory or at any other location, for example a central repository (see *lib* key in pipeline descriptor file). This may be more convenient, because the code is generally reused and independent of the actual project.


.. _pipeline:

Pipeline
========

A pipeline is a sequence of connected modules (a linked list) that represents a task, i.e. a unit of execution that runs on a single machine.
The sequence and structure of your pipeline is defined in a *.pipe* YAML `pipeline descriptor file`_. The input/output settings for each module are provided by additional *.handles* YAML `module descriptor files`_.


.. _pipeline-descriptor-file:

Pipeline descriptor file
------------------------

Jterator allows only very simplistic types of work-flow -  *pipeline* (somewhat similar to a UNIX-world pipeline). Description of such work-flow must be put sibling to the folder structure described above, i.e. inside the project folder. Recognizable file name must be *.pipe.yml*. Description is YAML format. 

Example of a *.pipe.yml* YAML descriptor file:

.. code-block:: yaml

    project:

        name: myJteratorProject
        lib: path/to/myRepository

    images:

        layers:
          - name: myExampleLayer1
            correct: true
          - name: myExampleLayer2
            correct: true

    pipeline:

        -   module: '{lib}/modules/myModule1.py'
            handles: handles/myModule1.handles
            active: true

        -   module: modules/myModule2.r
            handles: handles/myModule2.handles
            active: true

        -   module: '{lib}/modules/myModule3.m'
            handles: handles/myModule3.handles
            active: true

        -   module: modules/myModule4.jl
            handles: handles/myModule4.handles
            active: false


Note that the working directory is by default the project folder. You can provide either a full path to modules and handles files or a path relative to the project folder. You can also make use of the ``lib`` variable within the pipeline descriptor file to specify the location where you keep your module files (python format string, note that in this case you need parenthesis for strings containing ``{}`` brackets!). Best practice is to have the ``handles`` folder in you project directory, because the specifications in the handles descriptor files are usually project specific (this is even required for the user interface).   
The **images** section will create a list of jobs with filenames and id for each job that will be stored in a *.jobs.json* job descriptor file in JSON format.    

.. _modules:

Modules
=======

Modules are the actual executable code in your pipeline. Each module is simply a file that defines a function with the same name as the file.

.. _data:

Data
----

Measurement data are written to *.data.h5* HDF5 files to disk and stored in the *data* folder, a subdirectory of the project folder.

The name of the data file is available to the module as ``kwargs["data_file"]``.

.. _figures:

Figures
-------

Figures are written to *.fig* files to disk and stored in the *figures* folder, a subdirectory of the project folder.

To this end, modules can use the **savefigure** API function.   

The name of the figure file is available to the module as ``kwargs["figure_file"]``.


.. _module-expamples:

Module examples
---------------

**Python example**:     

.. code:: python

    import collections

    def myInitialPythonModule(InputImage, **kwargs):

        output = collections.namedtuple('Output', ['OutputImage'])
        return output(InputImage)


.. Note::

    Python functions should provide output as a `collections.namedtuple`.

**Matlab example**:     

.. code-block:: matlab

    function [OutputImage] = myMatlabModule(InputImage, varargin)

        OutputImage = InputImage;

    end


.. Note::

    Matlab functions should provide output as an array using ``[]`` notation.

.. Warning::

    Matlab functions cannot handle input or output of class `structure array`!

**R example**:

.. code-block:: R

    library(jtapi)

    myRModule <- function(InputImage, ...){

        dots <- list(...)

        output <- list()
        output[['OutputImage']] <- InputImage

        return(output)
    }


.. Note::
    
    R functions should provide output as a `list` with named members.


.. _module_descriptor-files:

Module descriptor files
-----------------------

Describe your modules in the *.handles* (YAML) descriptor files:        

.. code-block:: yaml

    input:

        - name: StringExample:
          class: parameter
          value: myString

        - name: IntegerExample
          class: parameter
          value: 1

        - name: PipelineInputExample
          class: pipeline
          value: myModule.InputData

        - name: ListExample
          class: parameter
          value: 
            - myString1
            - myString2
            - myString3

        - name: BoolExample
          class: parameter
          value: true

    output:

        - name: PipelineOutputExample
          class: pipeline
          value: myModule.OutputData

    plot: false 


There are two different **classes** of input/output arguments:

* **pipeline** corresponds to data that has to be produced upstream in the pipeline by another module. The corresponding value must be a string that has to be unique.
* **parameter** is an argument that is used to control the behavior of the module. It is module-specific and hence independent of other modules. It can be of any YAML supported type (integer, string, array, ...).


Jterator internally adds the following keys in order to make this information available to the modules:   

- **data_file**: absolute path to the HDF5 file, where data is stored    
- **figure_file**: filename of a potential figure. This enables the module to save a figure to a pre-defined location on disk, which the program is aware of
- **experiment_dir**: absolute path to the root directory of the currently processed experiment
- **plot**: boolean indicator whether a figure should be created or not
- **job_id**: one-based job identifier number


.. _developer-documentation:

***********************
Developer documentation
***********************

.. _naming-conventions:

Naming conventions
==================

Since Jterator is written in Python, we recommend following `PEP 0008 -- Style Guide for Python Code <https://www.python.org/dev/peps/pep-0008/>`_ for module and function names.
Therefore, we use short *all-lowercase* names for Jterator modules with *underscores* separating words if necessary, e.g. ``modulename`` or ``long_module_name``. See `naming conventions <https://www.python.org/dev/peps/pep-0008/#prescriptive-naming-conventions>`_.
In the case of Python, a jterator module is simply a Python module that contains a function with the same name as the module.
This approach also works for `Matlab function files <http://ch.mathworks.com/help/matlab/matlab_prog/create-functions-in-files.html>`_ and `R scripts <https://cran.r-project.org/doc/contrib/Lemon-kickstart/kr_scrpt.html>`_.


.. _module-outut:

Module output
=============

Output of modules is either returned or written to the provided HDF5 file. The required input parameter is made available to the modules as ``kwargs['data_file']`` in Python or ``varargin{1}`` in Matlab.

.. warning::

    Avoid writing to disk other than to the provided HDF5 file.


.. _non-pyhon-modules:

Non-Python modules
==================

Matlab
------


.. warning::

    Input/output arguments of class `structure array` are not supported.
