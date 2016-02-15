import time
import os
import logging
import importlib
from cached_property import cached_property
from gc3libs import Run
from gc3libs.workflow import SequentialTaskCollection
from gc3libs.workflow import ParallelTaskCollection
from gc3libs.workflow import StopOnError
from .description import WorkflowDescription
from .description import WorkflowStageDescription
from ..errors import WorkflowTransitionError
from ..jobs import CollectJob
from ..jobs import RunJobCollection
from ..jobs import MultiRunJobCollection

logger = logging.getLogger(__name__)


def load_step_interface(step_name):
    '''
    Load the command line interface for a `TissueMAPS` workflow step.

    Parameters
    ----------
    step_name: str
        name of the step, i.e. the corresponding subpackage in the "tmlib"
        package

    Returns
    -------
    tmlib.cli.CommandLineInterface
        command line interface

    Raises
    ------
    ImportError
        when subpackage with name `step_name` doesn't have a module named "cli"
    AttributeError
        when the "cli" module doesn't contain a step-specific
        implementation of the `CommandLineInterface` base class
    '''
    module_name = 'tmlib.%s.cli' % step_name
    logger.debug('load cli module "%s"' % module_name)
    module = importlib.import_module(module_name)
    class_name = step_name.capitalize()
    return getattr(module, class_name)


class WorkflowStep(SequentialTaskCollection):

    '''
    Class for a TissueMAPS workflow step, which is composed of a fixed
    collection of parallel run jobs and an optional collect job.
    Fixed means that the number of jobs and the arguments are known in advance.
    '''

    def __init__(self, name, run_jobs=None, collect_job=None):
        '''
        Initialize an instance of class WorkflowStep.

        Parameters
        ----------
        name: str
            name of the step
        run_jobs: tmlib.jobs.RunJobCollection, optional
            jobs for the *run* phase that should be processed in parallel
            (default: ``None``)
        collect_job: tmlib.jobs.CollectJob, optional
            job for the *collect* phase that should be processed after
            `run_jobs` have terminated successfully (default: ``None``)
        '''
        self.name = name
        tasks = list()
        if run_jobs is not None:
            if not(isinstance(run_jobs, RunJobCollection) or
                    isinstance(run_jobs, MultiRunJobCollection)):
                raise TypeError(
                            'Argument "run_jobs" must have type '
                            'tmlib.jobs.RunJobCollection or '
                            'tmlib.jobs.MultiRunJobCollection')
            tasks.append(run_jobs)
        if collect_job is not None:
            if not isinstance(collect_job, CollectJob):
                raise TypeError(
                            'Argument "collect_job" must have type '
                            'tmlib.jobs.CollectJob')
            tasks.append(collect_job)
        super(WorkflowStep, self).__init__(tasks=tasks, jobname=name)


class WorkflowStage(object):

    '''
    Base class for a TissueMAPS workflow stage.
    '''

    def __init__(self, name, experiment, verbosity, description=None):
        '''
        Initialize an instance of class WorkflowStage.

        Parameters
        ----------
        name: str
            name of the stage
        experiment: str
            configured experiment object
        verbosity: int
            logging verbosity index
        description: tmlib.tmaps.description.WorkflowStageDescription, optional
            description of the stage (default: ``None``)

        Note
        ----
        If `description` is not provided, there will be an attempt to obtain
        it from the user configuration file.

        Raises
        ------
        TypeError
            when `description` doesn't have type
            :py:class:`tmlib.tmaps.description.WorkflowStageDescription`
        ValueError
            when `description` is not provided and cannot be retrieved from
            the user configuration file

        See also
        --------
        :py:class:`tmlib.cfg.UserConfiguration`
        '''
        self.name = name
        self.experiment = experiment
        self.verbosity = verbosity
        if description is not None:
            if not isinstance(description, WorkflowStageDescription):
                raise TypeError(
                        'Argument "description" must have type '
                        'tmlib.tmaps.description.WorkflowStageDescription')
            self.description = description
        else:
            stages = self.experiment.user_cfg.workflow.stages
            names = [s.name for s in stages]
            index = names.index(self.name)
            self.description = stages[index]
        if self.description is None:
            raise ValueError(
                        'Description was not provided and could not be '
                        'determined from user configuration file.')
        self.expected_outputs = None

    def create_jobs_for_next_step(self, step_description):
        '''
        Create the jobs for a given workflow step.

        Parameters
        ----------
        step_description: tmlib.tmaps.description.WorkflowStepDescription
            description of the step

        Returns
        -------
        tmlib.tmaps.workflow.WorkflowStep
            jobs
        '''
        logger.info('create jobs for step "%s"', step_description.name)
        prog_name = step_description.name
        logger.debug('load program "%s"', prog_name)
        prog = load_step_interface(prog_name)
        logger.debug('create a program instance')
        prog_instance = prog(self.experiment, self.verbosity)

        logger.debug('call "init" method with configured arguments')
        prog_instance.init(step_description.args)
        # Check whether inputs of current step were generated by previous steps
        if not all([
                    os.path.exists(i)
                    for i in prog_instance.required_inputs
                ]):
            logger.error('required inputs were not generated')
            raise WorkflowTransitionError(
                        'inputs for step "%s" do not exist'
                        % step_description.name)

        # # Store the expected outputs to be later able to check whether they
        # # were actually generated
        # self.expected_outputs.append(prog_instance.expected_outputs)
        self.expected_outputs = prog_instance.expected_outputs

        logger.info('allocated time: %s', step_description.duration)
        logger.info('allocated memory: %d GB', step_description.memory)
        logger.info('allocated cores: %d', step_description.cores)
        jobs = prog_instance.create_jobs(
                        duration=step_description.duration,
                        memory=step_description.memory,
                        cores=step_description.cores)
        return jobs

    # def _determine_reason_for_job_failure(self, job):
    #     # check log file to figure out what went wrong
    #     err_file = os.path.join(job.output_dir, job.stderr)
    #     with open(err_file, 'r') as err:
    #         if re.search(r'^FAILED', err, re.MULTILINE):
    #             reason = 'Error'
    #         elif re.search(r'^TIMEOUT', err, re.MULTILINE):
    #             reason = 'Timeout'
    #         elif re.search(r'^[0-9]*\s*\bKilled\b', err, re.MULTILINE):
    #             reason = 'Memory'
    #         else:
    #             reason = 'Unknown'
    #     return reason

    # def can_transit_to_next_step(self, step):
    #     '''
    #     Check whether a step completed successfully.

    #     Parameters
    #     ----------
    #     step: tmlib.tmaps.workflow.WorkflowStep
    #         completed step

    #     Returns
    #     -------
    #     bool
    #         whether step completed successfully or failed
    #     '''
    #     # TODO: "correct" exitcode of jobs that have a non-zero exitcode
    #     # (e.g. ``None``) despite successful termination
    #     for phase in step.tasks:
    #         if (isinstance(phase, RunJobCollection) or
    #                 isinstance(phase, MultiRunJobCollection)):
    #             for job in phase.tasks:
    #                 if job.execution.exitcode != 0:
    #                     reason = self._determine_reason_for_job_failure(job)
    #         else:
    #             job = phase
    #             if job.execution.exitcode != 0:
    #                 reason = self._determine_reason_for_job_failure(job)
    #     return step.execution.exitcode != 0


class SequentialWorkflowStage(WorkflowStage, SequentialTaskCollection, StopOnError):

    '''
    Class for a sequential TissueMAPS workflow stage, which is composed of one
    or more dependent workflow steps that will be processed one after another.
    The number of jobs must be known for the first step of the stage,
    but it is usually unknown for the subsequent steps, since their input
    depends on the output of previous steps. Subsequent steps are thus build
    dynamically upon transition from one step to the next.
    '''

    def __init__(self, name, experiment, verbosity, description=None,
                 start_step=None):
        '''
        Initialize an instance of class SequentialWorkflowStage.

        Parameters
        ----------
        name: str
            name of the stage
        experiment: str
            configured experiment object
        verbosity: int
            logging verbosity index
        description: tmlib.tmaps.description.WorkflowStageDescription, optional
            description of the stage (default: ``None``)
        start_step: str or int, optional
            name or index of a step from where the stage should be started
            (default: ``None``)
        '''
        WorkflowStage.__init__(
                self, name=name, experiment=experiment, verbosity=verbosity)
        SequentialTaskCollection.__init__(
                self, tasks=None, jobname='%s' % name)
        self.start_step = start_step
        self._add_step(0)

    @property
    def n_steps(self):
        '''
        Returns
        -------
        int
            total number of steps
        '''
        return len(self.description.steps)

    @property
    def _start_index(self):
        if self.start_step is None:
            index = 0
        elif isinstance(self.start_step, basestring):
            step_names = [s.name for s in self.description.steps]
            if self.start_step not in step_names:
                raise ValueError('Invalid step: "%s"' % self.start_step)
            index = step_names.index(self.start_step)
        else:
            raise TypeError('Argument "start_step" must have type str.')
        return index

    @cached_property
    def _steps_to_process(self):
        steps_to_process = list()
        logger.info('start stage at step "%s"',
                    self.description.steps[self._start_index].name)
        for i, step in enumerate(self.description.steps):
            if i < self._start_index:
                continue
            steps_to_process.append(step)
        return steps_to_process

    def _add_step(self, index):
        if index > 0:
            # NOTE: Checking the existence of files can be problematic,
            # because NFS may lie. We try to circumvent this by waiting upon
            # transition to the next step, but this not be sufficient.
            if not all([os.path.exists(f) for f in self.expected_outputs]):
                logger.error('expected outputs were not generated')
                raise WorkflowTransitionError(
                             'outputs of previous step do not exist')
            logger.debug('create job descriptions for next step')
        task = self.create_jobs_for_next_step(self._steps_to_process[index])
        logger.debug('add jobs to the task list')
        self.tasks.append(task)

    def next(self, done):
        '''
        Progress to the next step.

        Parameters
        ----------
        done: int
            zero-based index of the last processed step

        Returns
        -------
        gc3libs.Run.State
        '''
        logger.info('step "%s" is done', self._steps_to_process[done].name)
        if done+1 < len(self._steps_to_process):
            wait = 120
            logger.debug('wait %d seconds', wait)
            time.sleep(wait)
            try:
                step_names = [s.name for s in self.description.steps]
                next_step_name = self._steps_to_process[done+1].name
                next_step_index = step_names.index(next_step_name)
                logger.info('transit to next step ({0} of {1}): "{2}"'.format(
                                next_step_index, self.n_steps, next_step_name))
                self._add_step(done+1)
            except Exception as error:
                logger.error('adding next step failed: %s', error)
                self.execution.exitcode = 1
                self.execution.returncode = 1
                logger.debug('set exitcode and returncode to one')
                logger.debug('set state to TERMINATED')
                return Run.State.TERMINATED

        return super(SequentialWorkflowStage, self).next(done)


class ParallelWorkflowStage(WorkflowStage, ParallelTaskCollection):

    '''
    Class for a parallel TissueMAPS workflow stage, which is composed of one
    or more independent workflow steps that will be processed at once.
    The number of jobs must be known for each step in advance.
    '''

    def __init__(self, name, experiment, verbosity, description=None):
        '''
        Initialize an instance of class ParallelWorkflowStage.

        Parameters
        ----------
        name: str
            name of the stage
        experiment: str
            configured experiment object
        verbosity: int
            logging verbosity index
        description: tmlib.tmaps.description.WorkflowStageDescription, optional
            description of the stage (default: ``None``)
        '''
        WorkflowStage.__init__(
                self, name=name, experiment=experiment, verbosity=verbosity)
        ParallelTaskCollection.__init__(
                self, tasks=None, jobname='%s' % name)
        self._build_tasks()

    def add(self, step):
        '''
        Add a step.

        Parameters
        ----------
        step: tmlibs.tmaps.workflow.WorkflowStep
            step that should be added

        Raises
        ------
        TypeError
            when `step` has wrong type
        '''
        if not isinstance(step, WorkflowStep):
            raise TypeError(
                        'Argument "step" must have type '
                        'tmlib.tmaps.workflow.WorkflowStep')
        super(ParallelWorkflowStage, self).add(step)

    def _build_tasks(self):
        for step in self.description.steps:
            step_jobs = self.create_jobs_for_next_step(step)
            self.add(step_jobs)


class Workflow(SequentialTaskCollection, StopOnError):

    def __init__(self, experiment, verbosity, description=None,
                 start_stage=None, start_step=None):
        '''
        Initialize an instance of class Workflow.

        Parameters
        ----------
        experiment: str
            configured experiment object
        verbosity: int
            logging verbosity index
        description: tmlib.tmaps.description.WorkflowDescription, optional
            description of the workflow (default: ``None``)
        start_stage: str or int, optional
            name or index of a stage from where the workflow should be
            started (default: ``None``)
        start_step: str or int, optional
            name or index of a step from where `start_stage` should be started
            (default: ``None``)

        Note
        ----
        If `description` is not provided, there will be an attempt to obtain
        it from the user configuration file.

        Raises
        ------
        TypeError
            when `description` doesn't have type
            :py:class:`tmlib.tmaps.description.WorkflowDescription`
        ValueError
            when `description` is not provided and cannot be retrieved from
            the user configuration file

        See also
        --------
        :py:class:`tmlib.cfg.UserConfiguration`
        '''
        super(Workflow, self).__init__(tasks=None, jobname=experiment.name)
        self.experiment = experiment
        self.verbosity = verbosity
        if description is not None:
            if not isinstance(description, WorkflowDescription):
                raise TypeError(
                        'Argument "description" must have type '
                        'tmlib.tmaps.description.WorkflowDescription')
            self.description = description
        else:
            self.description = self.experiment.user_cfg.workflow
        if self.description is None:
            raise ValueError(
                        'Description was not provided and could not be '
                        'determined from user configuration file.')
        self.start_stage = start_stage
        self.start_step = start_step
        if self.start_step is not None and self.start_stage is None:
            raise ValueError(
                        'Argument "start_step" also requires '
                        'argument "start_stage".')
        self.tasks = list()
        self._add_stage(0)

    @property
    def n_stages(self):
        '''
        Returns
        -------
        int
            total number of stages
        '''
        return len(self.description.stages)

    @property
    def _start_index(self):
        if self.start_stage is None:
            index = 0
        elif isinstance(self.start_stage, basestring):
            stage_names = [s.name for s in self.description.stages]
            if self.start_stage not in stage_names:
                raise ValueError('Invalid stage: "%s"' % self.start_stage)
            index = stage_names.index(self.start_stage)
        else:
            raise TypeError('Argument "start_stage" must have type str.')
        return index

    @cached_property
    def _stages_to_process(self):
        stages_to_process = list()
        stage_name = self.description.stages[self._start_index].name
        logger.info('start workflow at stage "%s"', stage_name)
        for i, stage in enumerate(self.description.stages):
            if i < self._start_index:
                continue
            stages_to_process.append(stage)
        return stages_to_process

    def _add_stage(self, index):
        stage = self._stages_to_process[index]
        logger.debug('create next stage "%s"', stage.name)
        if self.description.stages[self._start_index].name == stage.name:
            start_step = self.start_step
        else:
            start_step = None
        if stage.mode == 'sequential':
            logger.debug('build sequential workflow stage')
            task = SequentialWorkflowStage(
                        name=stage.name,
                        experiment=self.experiment,
                        verbosity=self.verbosity,
                        description=stage,
                        start_step=start_step)
        elif stage.mode == 'parallel':
            logger.debug('build parallel workflow stage')
            task = ParallelWorkflowStage(
                        name=stage.name,
                        experiment=self.experiment,
                        verbosity=self.verbosity,
                        description=stage)
        logger.debug('add stage to the workflow task list')
        self.tasks.append(task)

    def next(self, done):
        '''
        Progress to the next stage.

        Parameters
        ----------
        done: int
            zero-based index of the last processed stage

        Returns
        -------
        gc3libs.Run.State
        '''
        logger.info('stage "%s" is done', self._stages_to_process[done].name)
        if done+1 < len(self._stages_to_process):
            wait = 120
            logger.debug('wait %d seconds', wait)
            time.sleep(wait)
            try:
                stage_names = [s.name for s in self.description.stages]
                next_stage_name = self._stages_to_process[done+1].name
                next_stage_index = stage_names.index(next_stage_name) + 1
                logger.info('transit to next stage ({0} of {1}): "{2}"'.format(
                            next_stage_index, self.n_stages, next_stage_name))
                self._add_stage(done+1)
            except Exception as error:
                logger.error('adding next stage failed: %s', error)
                self.execution.exitcode = 1
                self.execution.returncode = 1
                logger.debug('set exitcode and returncode to 1')
                logger.debug('set state to TERMINATED')
                return Run.State.TERMINATED

        return super(Workflow, self).next(done)
