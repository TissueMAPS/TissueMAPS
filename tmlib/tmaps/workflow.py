import os
import re
import logging
import importlib
from cached_property import cached_property
from gc3libs import Run
from gc3libs.workflow import SequentialTaskCollection
from gc3libs.workflow import StopOnError
from ..errors import WorkflowNextStepError
from ..errors import WorkflowArgsError

logger = logging.getLogger(__name__)


class WorkflowStepArgs(object):

    def __init__(self, name=None, args=None):
        '''
        Initialize an instance of class WorkflowStep.

        Parameters
        ----------
        name: str, optional
            the name of the step
        args: dict, optional
            the arguments required for the step
        '''
        self._name = name
        self._args = args

    @property
    def name(self):
        '''
        Returns
        -------
        str
            name of the step

        Note
        ----
        Must correspond to a name of a `tmlib` command line program
        (subpackage).
        '''
        return self._name

    @name.setter
    def name(self, value):
        if not isinstance(value, basestring):
            raise TypeError('Attribute "value" must have type basestring')
        self._name = str(value)

    @property
    def args(self):
        '''
        Returns
        -------
        dict
            arguments required by the step (arguments that can be parsed
            to the "init" method of the corresponding *cli* class)

        Note
        ----
        Default values defined by the corresponding *init* subparser will
        be used in case an optional argument is not provided.

        See also
        --------
        `tmlib.cli`_
        '''
        return self._args

    @args.setter
    def args(self, value):
        if not isinstance(value, dict) or value is not None:
            raise TypeError('Attribute "args" must have type dict')
        self._args = value

    def __iter__(self):
        yield ('name', getattr(self, 'name'))
        yield ('args', getattr(self, 'args'))


class Workflow(SequentialTaskCollection, StopOnError):

    def __init__(self, experiment, virtualenv, verbosity):
        '''
        Initialize an instance of class Workflow.

        Parameters
        ----------
        experiment: str
            configured experiment object
        virtualenv: str
            name of a virtual environment that needs to be activated
        verbosity: int
            logging level verbosity

        Returns
        -------
        Workflow
        '''
        super(Workflow, self).__init__(
            tasks=None, jobname='tmaps')
        self.experiment = experiment
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
            command for each step of the workflow

        Note
        ----
        Arguments can be set in the user configuration file.
        '''
        workflow = self.experiment.user_cfg.workflow
        commands = list()
        logger.info('build workflow based on user configuration')
        for step in workflow:
            logger.debug('add step "%s" to workflow', step.name)
            cmd = [step.name]
            cmd.extend(['-v' for x in xrange(self.verbosity)])
            cmd.append(self.experiment.dir)
            cmd.append('init')
            if step.args:
                for k, v in step.args.iteritems():
                    if v or v == 0:  # zero would be considered ``False``
                        cmd.append('--%s' % k)
                    if not isinstance(v, bool) and v is not None:
                        cmd.append(str(v))
            # Test whether arguments are specified correctly.
            parser = self._get_argparser(cmd[0])
            try:
                parser.parse_args(cmd[1:])
            except SystemExit:
                raise WorkflowArgsError(
                        'Arguments for step "%s" are specified incorrectly'
                        % step.name)
            commands.append(cmd)
        return commands

    @property
    def _package_name(self):
        return re.search('^([^.]+)', self.__module__).group(1)

    def _get_argparser(self, prog_name):
        package_name = self._package_name
        module_name = '%s.%s.argparser' % (package_name, prog_name)
        logger.debug('load argparser module "%s"' % module_name)
        module = importlib.import_module(module_name)
        parser = module.parser
        return parser

    def _create_jobs_for_step(self, init_command):
        prog_name = init_command[0]
        logger.debug('create jobs for step {0}'.format(prog_name))
        package_name = self._package_name
        module_name = '%s.%s.cli' % (package_name, prog_name)
        logger.debug('load cli module "%s"' % module_name)
        module = importlib.import_module(module_name)
        class_name = prog_name.capitalize()

        parser = self._get_argparser(prog_name)
        init_args = parser.parse_args(init_command[1:])
        init_cli_instance = getattr(module, class_name)(init_args)

        # Check whether inputs of current step were generated by previous steps
        if not all([
                    os.path.exists(i)
                    for i in init_cli_instance.required_inputs
                ]):
            logger.error('required inputs were not generated')
            raise WorkflowNextStepError('required inputs do not exist')

        # Create job_descriptions for new step
        getattr(init_cli_instance, init_args.method_name)()

        # Store the expected outputs to be later able to check whether they
        # were actually generated
        self.expected_outputs.append(init_cli_instance.expected_outputs)

        # Build "submit" command
        submit_command = list()
        submit_command.extend(init_command[:init_command.index('init')])
        submit_command.append('submit')
        if self.virtualenv:
            submit_command.extend(['--virtualenv', self.virtualenv])

        parser = self._get_argparser(prog_name)
        submit_args = parser.parse_args(submit_command[1:])
        submit_cli_instance = getattr(module, class_name)(submit_args)
        # The "jobs" attribute returns a SequentialTaskCollection
        return submit_cli_instance.jobs

    def _add_step(self, index):
        if index > 0:
            if not all([os.path.exists(f) for f in self.expected_outputs[-1]]):
                logger.error('expected outputs were not generated')
                raise WorkflowNextStepError(
                             'outputs of previous step do not exist')
        logger.debug('create job descriptions for next step')
        init_command = self.commands[index]
        logger.debug('create jobs for next step and add them to the task list')
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
