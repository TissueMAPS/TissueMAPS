import os
import logging
import importlib
from cached_property import cached_property
from gc3libs import Run
from gc3libs.workflow import SequentialTaskCollection
from gc3libs.workflow import StopOnError
from ..errors import WorkflowNextStepError

logger = logging.getLogger(__name__)


def load_program(prog_name):
    '''
    Load a `TissueMAPS` command line program.

    Parameters
    ----------
    prog_name: str
        name of the program, i.e. the name of corresponding subpackage in the
        "tmlib" package

    Returns
    -------
    tmlib.cli.CommandLineInterface
        command line program

    Raises
    ------
    ImportError
        when subpackage with name `prog_name` doesn't have a module named "cli"
    AttributeError
        when the "cli" module doesn't contain a program-specific
        implementation of the `CommandLineInterface` base class
    '''
    module_name = 'tmlib.%s.cli' % prog_name
    logger.debug('load cli module "%s"' % module_name)
    module = importlib.import_module(module_name)
    class_name = prog_name.capitalize()
    return getattr(module, class_name)


def load_method_args(method_name):
    '''
    Load general arguments that can be parsed to a method of
    an implemented subclass of a :py:class:`tmlib.cli.CommandLineInterface`
    base class

    Parameters
    ----------
    method_name: str
        name of the method

    Returns
    -------
    tmlib.args.Args
        argument container

    Raises
    ------
    AttrbuteError
        when the "args" module doesn't contain a method-specific
        implementation of the `Args` base class
    '''
    module_name = 'tmlib.args'
    module = importlib.import_module(module_name)
    class_name = '%sArgs' % method_name.capitalize()
    return getattr(module, class_name)


def load_var_method_args(prog_name, method_name):
    '''
    Load additional, variable program-specific arguments that can be parsed to
    a method of an implemented subclass of a
    :py:class:`tmlib.cli.CommandLineInterface` base class.

    Parameters
    ----------
    prog_name: str
        name of the program
    method_name: str
        name of the method

    Returns
    -------
    tmlib.args.Args
        argument container

    Note
    ----
    Returns ``None`` when the "args" module in the subpackage with name
    `prog_name` doesn't contain a program- and method-specific implementation
    of the `Args` base class.

    Raises
    ------
    ImportError
        when subpackage with name `prog_name` doesn't have a module named "args"
    '''
    package_name = 'tmlib.%s' % prog_name
    module_name = 'tmlib.%s.args' % prog_name
    importlib.import_module(package_name)
    module = importlib.import_module(module_name)
    class_name = '%s%sArgs' % (prog_name.capitalize(),
                               method_name.capitalize())
    try:
        return getattr(module, class_name)
    except AttributeError:
        return None


class Workflow(SequentialTaskCollection, StopOnError):

    def __init__(self, experiment, description=None,
                 start_stage=None, start_step=None):
        '''
        Initialize an instance of class Workflow.

        Parameters
        ----------
        experiment: str
            configured experiment object
        description: tmlib.cfg.WorkflowDescription, optional
            description of the workflow that should be (default: ``None``)
        start_stage: str or int, optional
            name or index of a stage from where the workflow should be
            started (default: ``None``)
        start_step: str or int, optional
            name or index of a step within `stage` from where the workflow
            should be started (default: ``None``)

        Note
        ----
        If no `description` is provided, the description is
        obtained from the user configuration settings file.

        See also
        --------
        :py:mod:`tmlib.cfg`
        '''
        super(Workflow, self).__init__(tasks=None, jobname='tmaps')
        self.experiment = experiment
        self.workflow = description
        if self.workflow is None:
            self.workflow = self.experiment.user_cfg.workflow
        self.start_stage = start_stage
        self.start_step = start_step
        self.tasks = list()
        self.expected_outputs = list()
        self._add_step(0)

    @cached_property
    def steps_to_process(self):
        '''
        Returns
        -------
        List[WorkflowStepDescription]
            description of each step of the workflow that should be processed

        Note
        ----
        Arguments can be set in the user configuration file.
        '''
        steps_to_process = list()
        if self.start_stage is None:
            stage_ix = 0
        elif isinstance(self.start_stage, basestring):
            stage_names = [s.name for s in self.workflow.stages]
            stage_ix = stage_names.index(self.start_stage)
        elif isinstance(self.start_stage, int):
            stage_ix = self.start_stage
        else:
            raise TypeError('Argument "start_stage" must have type str or int.')
        stage = self.workflow.stages[stage_ix]
        if self.start_step is None:
            step_ix = 0
        elif isinstance(self.start_step, basestring):
            step_names = [s.name for s in stage.steps]
            step_ix = step_names.index(self.start_step)
        elif isinstance(self.start_step, int):
            step_ix = self.start_step
        else:
            raise TypeError('Argument "start_step" must have type str or int.')
        logger.info('start workflow at stage "%s" step "%s"',
                    stage.name, stage.steps[step_ix].name)
        for i, stage in enumerate(self.workflow.stages):
            if i < stage_ix:
                continue
            for j, step in enumerate(stage.steps):
                if i == stage_ix and j < step_ix:
                    continue
                logger.debug('add step "%s" to workflow', step.name)
                steps_to_process.append(step)
        return steps_to_process

    def _create_jobs_for_next_step(self, step):
        logger.debug('create jobs for step {0}'.format(step.name))
        prog_name = step.name
        logger.debug('load program "%s"', prog_name)
        prog = load_program(prog_name)
        logger.debug('create a program instance')
        prog_instance = prog(self.experiment, self.workflow.verbosity)

        # Check whether inputs of current step were generated by previous steps
        if not all([
                    os.path.exists(i)
                    for i in prog_instance.required_inputs
                ]):
            logger.error('required inputs were not generated')
            raise WorkflowNextStepError('required inputs do not exist')

        logger.debug('call "init" method with configured arguments')
        prog_instance.init(step.args)

        # Store the expected outputs to be later able to check whether they
        # were actually generated
        self.expected_outputs.append(prog_instance.expected_outputs)

        logger.debug('build GC3Pie jobs')
        jobs = prog_instance.build_jobs(virtualenv=self.workflow.virtualenv)
        # jobs: gc3libs.workflow.SequentialTaskCollection
        return jobs

    def _add_step(self, index):
        if index > 0:
            if not all([os.path.exists(f) for f in self.expected_outputs[-1]]):
                logger.error('expected outputs were not generated')
                raise WorkflowNextStepError(
                             'outputs of previous step do not exist')
        logger.debug('create job descriptions for next step')
        task = self._create_jobs_for_next_step(self.steps_to_process[index])
        logger.debug('add jobs to the workflow task list')
        self.tasks.append(task)

    def next(self, done):
        '''
        Progress to the next step of the workflow.

        Parameters
        ----------
        done: int
            zero-based index of the last processed step

        Returns
        -------
        gc3libs.Run.State
        '''
        # TODO: resubmission
        # RetriableTask: overwrite "retry" method and adapt resubmission
        # criteria such as memory or time requirements
        # Workflow description: YAML mapping for each step with "command",
        # "time", "memory", "resubmit", "active" keys
        if done+1 < len(self.steps_to_process):
            try:
                logger.info('progress to next step ({0} of {1}): "{2}"'.format(
                                (done+1), len(self.steps_to_process),
                                self.steps_to_process[done+1].name))
                self._add_step(done+1)
            except Exception as error:
                logger.error('adding next step failed: %s', error)
                self.execution.exitcode = 1
                logger.debug('set exitcode to one')
                logger.debug('set state to TERMINATED')
                return Run.State.TERMINATED

        return super(Workflow, self).next(done)
