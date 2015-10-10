import os
import logging
import importlib
from gc3libs import Run
from gc3libs.workflow import SequentialTaskCollection
from gc3libs.workflow import StopOnError
from ..readers import WorkflowDescriptionReader
from ..cluster import BasicClusterRoutines
from ..errors import WorkflowNextStepError

logger = logging.getLogger(__name__)


class ClusterWorkflowManager(SequentialTaskCollection, StopOnError):

    '''
    Class for reading workflow descriptions from a YAML file.
    '''

    def __init__(self, experiment, virtualenv, verbosity):
        '''
        Initialize an instance of class ClusterWorkflowManager.

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
        ClusterWorkflowManager
        '''
        super(ClusterWorkflowManager, self).__init__(
            tasks=None, jobname='tmaps')
        self.experiment = experiment
        self.virtualenv = virtualenv
        self.verbosity = verbosity
        self.tasks = list()
        self.expected_outputs = list()
        self._add_step(0)

    @property
    def workflow_file(self):
        '''
        Returns
        -------
        str
            name of the file that describes the workflow

        Note
        ----
        The file is located in the root directory of the experiment folder.
        '''
        self._workflow_file = '{experiment}.workflow'.format(
                                    experiment=self.experiment.name)
        return self._workflow_file

    @property
    def workflow_description(self):
        '''
        Returns
        -------
        List[str]
            commands for each individual step of the workflow
        '''
        logger.debug('read workflow description from file: {0}'.format(
                        self.workflow_file))
        with WorkflowDescriptionReader(self.experiment.dir) as reader:
            workflow = reader.read(self.workflow_file)
        self._workflow_description = [
            step.format(experiment_dir=self.experiment.dir).split()
            for step in workflow
        ]
        return self._workflow_description

    def _create_jobs_for_step(self, step_desciption):
        package_name = 'tmlib'
        prog_name = step_desciption[0]
        logger.debug('create jobs for step {0}'.format(prog_name))
        argparser_module_name = '%s.%s.argparser' % (package_name, prog_name)
        logger.debug('load argparser module "%s"' % argparser_module_name)
        argparser_module = importlib.import_module(argparser_module_name)
        parser = argparser_module.parser
        parser.prog = prog_name
        cli_module_name = '%s.%s.cli' % (package_name, prog_name)
        logger.debug('load cli module "%s"' % cli_module_name)
        cli_module = importlib.import_module(cli_module_name)

        init_command = step_desciption[1:]
        logger.debug('parse arguments to cli class instance '
                     'for the "init" method: {0}'.format(init_command))
        # TODO: add additional arguments using the format string method
        # with a dictionary read from the user.cfg file
        args = parser.parse_args(init_command)
        cli_class_inst = getattr(cli_module, prog_name.capitalize())(args)

        # Check whether inputs of current step were produced upstream
        if not all([os.path.exists(i) for i in cli_class_inst.required_inputs]):
            logger.error('required inputs were not produced upstream')
            raise WorkflowNextStepError('required inputs do not exist')

        # Create job_descriptions for new step
        getattr(cli_class_inst, args.method_name)()

        # Store the expected outputs to be later able to check whether they
        # were actually generated
        self.expected_outputs.append(cli_class_inst.expected_outputs)

        # Take the base of the "init" command to get the positional arguments
        # of the main program parser and extend it with additional
        # arguments required for submit subparser
        submit_command = list()
        if self.verbosity > 0:
            submit_command.append('-v')
        submit_command.extend(init_command[:init_command.index('init')])
        submit_command.append('submit')
        if self.virtualenv:
            submit_command.extend(['--virtualenv', self.virtualenv])
        logger.debug('parse arguments to cli class instance '
                     'for the "submit" method: {0}'.format(submit_command))
        args = parser.parse_args(submit_command)
        cli_class_inst = getattr(cli_module, prog_name.capitalize())(args)
        # Calling the "jobs" method returns a SequentialTaskCollection
        return cli_class_inst.jobs

    def _add_step(self, index):
        if index > 0:
            if not all([os.path.exists(f) for f in self.expected_outputs[-1]]):
                logger.error('expected outputs were not generated')
                raise WorkflowNextStepError(
                             'outputs of previous step do not exist')
        logger.debug('create job descriptions for next step')
        step_desciption = self.workflow_description[index]
        logger.debug('create jobs for next step and add them to the task list')
        task = self._create_jobs_for_step(step_desciption)
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

        if done+1 < len(self.workflow_description):
            logger.info('progress to next step ({0} of {1}): "{2}"'.format(
                            (done+1), len(self.workflow_description),
                            self.workflow_description[done+1][0]))
            try:
                self._add_step(done+1)
            except Exception as error:
                logger.error('adding next step failed: %s', error)
                self.execution.exitcode = 1
                logger.debug('set exitcode to one')
                logger.debug('set state to TERMINATED')
                return Run.State.TERMINATED

        return super(ClusterWorkflowManager, self).next(done)


class WorkflowClusterRoutines(BasicClusterRoutines):

    def __init__(self, experiment, prog_name):
        '''
        Initialize an instance of class WorkflowClusterRoutines.

        Parameters
        ----------
        experiment: Experiment
            configured experiment object
        prog_name: str
            name of the corresponding program (command line interface)
        '''
        super(WorkflowClusterRoutines, self).__init__(experiment)
        self.experiment = experiment
        self.prog_name = prog_name

    @property
    def project_dir(self):
        '''
        Returns
        -------
        str
            directory where *.job* files and log output will be stored
        '''
        self._project_dir = os.path.join(self.experiment.dir, 'tmaps')
        if not os.path.exists(self._project_dir):
            logging.debug('create project directory: %s' % self._project_dir)
            os.mkdir(self._project_dir)
        return self._project_dir
