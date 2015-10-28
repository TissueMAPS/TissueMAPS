import os
import logging
import importlib
from cached_property import cached_property
from gc3libs import Run
from gc3libs.workflow import SequentialTaskCollection
from gc3libs.workflow import StopOnError
from ..errors import WorkflowNextStepError
from ..errors import WorkflowArgsError

logger = logging.getLogger(__name__)


def dict_to_command(d):
    '''
    Convert arguments provided as a dictionary into a list of command strings,
    which can be used as input argument for the
    `parse_args() <https://argparse.googlecode.com/svn/trunk/doc/parse_args.html>`_
    method of the argparser package.

    Parameters
    ----------
    d: dict
        arguments as key-value pairs

    Returns
    -------
    List[str]
        arguments as sub-commands

    Note
    ----
    For boolean arguments only the key will be appended to the command and only
    in case the value is ``True``.

    Examples
    --------
    >>>dict_to_command({"a": "bla", "b": True, "c": False})
    ["--a", "bla", "--b"]
    '''
    command = list()
    for k, v in d.iteritems():
        if isinstance(v, bool):
            if v:
                command.append('--%s' % str(k))
        command.extend(['--%s' % str(k), str(v)])
    return command


def load_parser(prog_name):
    '''
    Load a
    `parser <https://docs.python.org/3/library/argparse.html#argparse.ArgumentParser>`_
    object of a TissueMAPS command line program.

    Parameters
    ----------
    prog_name: str
        name of the program, i.e. the name of corresponding subpackage in the
        "tmlib" package

    Returns
    -------
    argparse.ArgumentParser
        the loaded parser object

    Raises
    ------
    ImportError
        when subpackage with name `prog_name` doesn't have a module named
        "argparser"
    AttributeError
        when the "argparser" module doesn't contain an attribute named "parser"

    Examples
    --------
    >>>load_parser('align')
    '''
    module_name = 'tmlib.%s.argparser' % prog_name
    logger.debug('load argparser module "%s"' % module_name)
    module = importlib.import_module(module_name)
    return module.parser


def load_program(prog_name):
    '''
    Load a TissueMAPS command line program.

    Parameters
    ----------
    prog_name: str
        name of the program, i.e. the name of corresponding subpackage in the
        "tmlib" package

    Raises
    ------
    ImportError
        when subpackage with name `prog_name` doesn't have a module named "cli"
    AttributeError
        when the "cli" module doesn't contain a class with name `prog_name`

    Returns
    -------
    tmlib.cli.CommandLineInterface
        command line program, i.e. an instance of a subclass of the abstract
        base class :mod:`tmlib.cli.CommandLineInterface`
    '''
    module_name = 'tmlib.%s.cli' % prog_name
    logger.debug('load cli module "%s"' % module_name)
    module = importlib.import_module(module_name)
    class_name = prog_name.capitalize()
    return getattr(module, class_name)


class Workflow(SequentialTaskCollection, StopOnError):

    def __init__(self, experiment, stage, step, virtualenv, verbosity):
        '''
        Initialize an instance of class Workflow.

        Parameters
        ----------
        experiment: str
            configured experiment object
        stage: str or int,
            name or index of the stage from where the workflow should be
            started
        step: str or int
            name or index of the step within `stage` from where the workflow
            should be started
        virtualenv: str
            name of a virtual environment that needs to be activated
        verbosity: int
            logging level verbosity

        Returns
        -------
        tmlib.tmaps.Workflow
        '''
        super(Workflow, self).__init__(tasks=None, jobname='tmaps')
        self.experiment = experiment
        self.stage = stage
        self.step = step
        self.virtualenv = virtualenv
        self.verbosity = verbosity
        self.tasks = list()
        self.expected_outputs = list()
        self._add_step(0)

    @cached_property
    def commands(self):
        '''
        Build a command in the form of a list of argument strings as required
        by the
        `parse_args() <https://docs.python.org/3/library/argparse.html#argparse.ArgumentParser.parse_args>`_
        method.

        Returns
        -------
        List[List[str]]
            command for each step of the specified workflow stage

        Note
        ----
        Arguments can be set in the user configuration file.
        '''
        workflow = self.experiment.user_cfg.workflow
        commands = list()
        logger.info('build workflow based on user configuration')
        if isinstance(self.stage, basestring):
            stage_ix = [s.name for s in workflow.stages].index(self.stage)
        else:
            stage_ix = self.stage
        stage = workflow.stages[stage_ix]
        logger.info('start workflow at stage "%s"', stage.name)
        if self.step is None:
            self.step = 0
        if isinstance(self.step, basestring):
            step_ix = [s.name for s in stage.steps].index(self.step)
        else:
            step_ix = self.step
        logger.info('start stage "%s" at step "%s"',
                    stage.name, stage.steps[step_ix].name)
        for i, stage in enumerate(workflow.stages):
            if i < stage_ix:
                continue
            for j, step in enumerate(stage.steps):
                if j < step_ix:
                    continue
                logger.debug('add step "%s" to workflow', step.name)
                cmd = [step.name]
                cmd.extend(['-v' for x in xrange(self.verbosity)])
                cmd.append(self.experiment.dir)
                cmd.append('init')
                if step.args:
                    cmd.extend(dict_to_command(step.args))
                # Test whether arguments are specified correctly.
                parser = load_parser(cmd[0])
                try:
                    parser.parse_args(cmd[1:])
                except SystemExit as error:
                    raise WorkflowArgsError(
                        'Arguments for step "%s" are specified incorrectly:\n%s'
                        % (step.name, str(error)))
                commands.append(cmd)
        return commands

    def _create_jobs_for_step(self, init_command):
        prog_name = init_command[0]
        logger.debug('create jobs for step {0}'.format(prog_name))
        prog = load_program(prog_name)
        parser = load_parser(prog_name)
        init_args = parser.parse_args(init_command[1:])
        init_prog = prog(init_args)

        # Check whether inputs of current step were generated by previous steps
        if not all([
                    os.path.exists(i)
                    for i in init_prog.required_inputs
                ]):
            logger.error('required inputs were not generated')
            raise WorkflowNextStepError('required inputs do not exist')

        # Create job_descriptions for new step
        getattr(init_prog, init_args.method_name)()

        # Store the expected outputs to be later able to check whether they
        # were actually generated
        self.expected_outputs.append(init_prog.expected_outputs)

        # Build "submit" command
        submit_command = list()
        submit_command.extend(init_command[:init_command.index('init')])
        submit_command.append('submit')
        if self.virtualenv:
            submit_command.extend(['--virtualenv', self.virtualenv])

        # Create submission program
        submit_args = parser.parse_args(submit_command[1:])
        submit_prog = prog(submit_args)
        # Return "jobs" (gc3libs.workflow.SequentialTaskCollection)
        return submit_prog.jobs

    def _add_step(self, index):
        if index > 0:
            if not all([os.path.exists(f) for f in self.expected_outputs[-1]]):
                logger.error('expected outputs were not generated')
                raise WorkflowNextStepError(
                             'outputs of previous step do not exist')
        logger.debug('create job descriptions for next step')
        init_command = self.commands[index]
        logger.debug('add jobs to the task list')
        task = self._create_jobs_for_step(init_command)
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

        if done+1 < len(self.commands):
            logger.info('progress to next step ({0} of {1}): "{2}"'.format(
                            (done+1), len(self.commands),
                            self.commands[done+1][0]))
            try:
                self._add_step(done+1)
            except Exception as error:
                logger.error('adding next step failed: %s', error)
                self.execution.exitcode = 1
                logger.debug('set exitcode to one')
                logger.debug('set state to TERMINATED')
                return Run.State.TERMINATED

        return super(Workflow, self).next(done)
