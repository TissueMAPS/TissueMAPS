'''A  `workflow` is a sequence of computational tasks
that should be processed on a cluster computer.
It is composed of one or more `stages`, which are themselves composed of one
or more `steps`. A `step` represents a collection of batch jobs that
should be processed in parallel. A `stage` bundles mutliple `steps` into a
logical processing unit taking potential dependencies between `steps` into
account.

Each `step` represents a subpackage, which must implement the following
modules:

    * **api**: must implement :py:class:`tmlib.workflow.api.ClusterRoutines`
    and decorate it with :py:function:`tmlib.workflow.registry.api`
    * **args**: must implement :py:class`tmlib.workflow.args.BatchArguments` and
    :py:class:`tmlib.workflow.args.SubmissionArguments` and decorate them with
    :py:function:`tmlib.workflow.registry.batch_args` and
    :py:function:`tmlib.workflow.registry.submission_args`, respectively
    * **cli**: must implement :py:class:`tmlib.workflow.cli.CommandLineInterface`

This automatically registers each step and enables using it via the
command line and/or integrating it into a workflow.
'''
import os
import glob

from workflow import Workflow
from workflow import WorkflowStep
from workflow import ParallelWorkflowStage
from workflow import SequentialWorkflowStage
from engine import BgEngine


def get_steps():
    '''Lists the implemented workflow steps.

    Returns
    -------
    List[str]
        names of steps
    '''
    root = os.path.dirname(__file__)
    def is_package(d):
        d = os.path.join(root, d)
        return os.path.isdir(d) and glob.glob(os.path.join(d, '__init__.py*'))
    return filter(is_package, os.listdir(root))



