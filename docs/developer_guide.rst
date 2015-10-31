
.. _subpackages

Subpackages
===========

Each subpackage represents a :term:`step` and provides an application programming interface (**API**) and a command-line interface (**CLI**).
It must contain the following modules:

- **args**: Defines the arguments that can be parsed to the step.
- **argparser**: Serves an instance of class `argparse.ArgumentParser <https://docs.python.org/3/library/argparse.html#argumentparser-objects>`_ that processes arguments provided via the command line and parses them to the *cli* class. The parser has the same name as the package and each subparser has a corresponding method in the *cli* class.
- **cli**: The *cli* class gets initialized with the parsed arguments (either from the command line or dynamically within a :term:`workflow`) and the method with the name of the specified subparser gets called. The method in turn initializes an instance of the *api* class and delegates the actual processing to lower level methods of this class. Of particular importance for the workflow is the *init* method, which handles arguments for fine-tuning of the step and creates persistent job descriptions on disk.
- **api**: The *api* class provides methods for all *GC3Pie* related magic, such as creation and submission of jobs.


The *api* and *cli* classes inherit from the `CommandLineInterface` and `ClusterRoutines` base classes, respectively. This approach makes it easy to further extend the workflow by additional steps and allows a common syntax for command line calls:

.. code-block:: bash

    <class_name> <class_args> <method_name> <method_args>

where

* **class_name** is the name of the main parser corresponding to the *cli* class of an individual step
* **class_args** are arguments that are handled by the main parser, such as the logging verbosity level or the path to the directory of the experiment that should be processed, which are used to instantiate the corresponding *api* class
* **method_name** is the name of a subparser corresponding to a method of the *cli* class
* **method_args** are arguments that are handled by the subparser and are forwarded to the methods of the *api* class

.. _documentation

Documentation
=============

We use `Sphinx <http://sphinx-doc.org/index.html>`_ in combination with the `Napoleon extension <https://pypi.python.org/pypi/sphinxcontrib-napoleon>`_ for support of the `reStructuredText NumPy style <https://github.com/numpy/numpy/blob/master/doc/HOWTO_DOCUMENT.rst.txt#docstring-standard>`_.
