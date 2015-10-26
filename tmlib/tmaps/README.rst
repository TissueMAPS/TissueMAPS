A `tmaps` workflow represents a `GC3Pie workflow <http://gc3pie.readthedocs.org/en/latest/programmers/api/gc3libs/workflow.html>`_, which enables the combination of several individual processing steps (which are themselves GC3Pie workflows) to submit and monitor them as a single job.

Define a workflow
=================

A workflow is defined within an experiment-specific user configuration file. The user needs to create this file in the experiment root directory. For details see `UserConfiguration` class in the `tmlib.cfg <../cfg.py>`_ module and `WorkflowStepArgs` class in the `tmlib.tmaps.workflow module <./workflow.py>`_.

The file must specify a mapping in `YAML <http://yaml.org/>`_ format and provide the *name* and the arguments (*args*) for each step of the *workflow*.

The `user.cfg.template <./../user.cfg.template>`_ file is an example template for processing image files created by *cellvoyager* microscopes and multiple acquisition cycles, where images with channel ID ``0`` and cycle ID ``1`` are used as reference for image registration:

The list of required and optional arguments and help for each step is available via the corresponding command line interface:

.. code::

    <name> ./ init -h


.. note::
    The positional argument *experiment_dir* has to be provided in order to be able to display the help message for the *init* subparser.


Submit a workflow
=================


Once defined, a workflow can be submitted from the command line:

.. code::

    tmaps -v <experiment_dir> submit


This submits the jobs of each step once the previous step has successfully terminated and continuously monitors job status.





