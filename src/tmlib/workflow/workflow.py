import time
import os
import logging
import importlib
import copy
import sys
import traceback
import gc3libs
from cached_property import cached_property
from gc3libs.workflow import SequentialTaskCollection
from gc3libs.workflow import ParallelTaskCollection
from gc3libs.workflow import AbortOnError

import tmlib.models
from tmlib.utils import assert_type
from tmlib.workflow import get_step_api
from tmlib.workflow.description import WorkflowDescription
from tmlib.workflow.description import WorkflowStageDescription
from tmlib.errors import WorkflowTransitionError
from tmlib.readers import YamlReader
from tmlib.workflow.jobs import InitJob
from tmlib.workflow.jobs import CollectJob
from tmlib.workflow.jobs import RunJobCollection

logger = logging.getLogger(__name__)


class State(object):

    '''Mixin class that provides convenience properties to determine whether
    a task is in a given state.'''

    @property
    def is_terminated(self):
        '''bool: whether the step is in state TERMINATED'''
        return self.execution.state == gc3libs.Run.State.TERMINATED

    @property
    def is_running(self):
        '''bool: whether the step is in state RUNNING'''
        return self.execution.state == gc3libs.Run.State.RUNNING

    @property
    def is_stopped(self):
        '''bool: whether the step is in state STOPPED'''
        return self.execution.state == gc3libs.Run.State.STOPPED

    @property
    def is_submitted(self):
        '''bool: whether the step is in state SUBMITTED'''
        return self.execution.state == gc3libs.Run.State.SUBMITTED

    @property
    def is_new(self):
        '''bool: whether the job is state NEW'''
        return self.execution.state == gc3libs.Run.State.NEW


class WorkflowStep(AbortOnError, SequentialTaskCollection, State):

    '''A *workflow step* represents a collection of computational tasks
    that should be processed in parallel on a cluster, i.e. one parallelization
    step within a larger, more complex workflow.
    '''

    def __init__(self, name, experiment_id, verbosity, submission_id, user_name,
            description, requires_init=True):
        '''
        Parameters
        ----------
        name: str
            name of the step
        experiment_id: int
            ID of the processed experiment
        verbosity: int
            logging verbosity index
        submission_id: int
            ID of the corresponding submission
        user_name: str
            name of the submitting user
        description: tmlib.tmaps.description.WorkflowStepDescription
            description of the step
        requires_init: bool, optional
            whether an "init" job is required (default: ``True``)
        '''
        super(WorkflowStep, self).__init__(tasks=[], jobname=name)
        self.name = name
        self.experiment_id = experiment_id
        self.verbosity = verbosity
        self.submission_id = submission_id
        self.user_name = user_name
        self.description = description
        self.requires_init = requires_init
        if self.requires_init:
            self.create_init_job()
        self.initialize_run_jobs()
        import ipdb; ipdb.set_trace()
        # TODO: how can we figure out whether the step has a collect phase?
        self.create_collect_job()
        # TODO: this whole approach with requires_init should be optimized
        # Pre-create phases, such that progress is correct???
        self._current_task = 0

    @property
    def init_job(self):
        '''tmlib.workflow.jobs.InitJob: job for the "init" phase'''
        if not self.requires_init:
            raise WorkflowTransitionError(
                'Workflow step "%s" was configured without "init" phase.'
                % self.name
            )
        try:
            return self.tasks[0]
        except IndexError:
            raise WorkflowTransitionError(
                'Workflow step "%s" doesn\'t have a "init" job.' % self.name
            )

    @init_job.setter
    def init_job(self, value):
        if not self.requires_init:
            raise WorkflowTransitionError(
                'Workflow step "%s" was configured without "init" phase.'
                % self.name
            )

        if value is not None:
            if not isinstance(value, InitJob):
                raise TypeError(
                    'Attribute "init_job" must have type '
                    'tmlib.workflow.jobs.InitJob'
                )
            if len(self.tasks) == 0:
                self.tasks.append(value)
            else:
                self.tasks[0] = value

    @property
    def run_jobs(self):
        '''tmlib.workflow.jobs.RunJobCollection: collection of jobs for the
        "run" phase
        '''
        try:
            if self.requires_init:
                return self.tasks[1]
            else:
                return self.tasks[0]
        except IndexError:
            raise WorkflowTransitionError(
                'Workflow step "%s" doesn\'t have any "run" jobs.' % self.name
            )

    @run_jobs.setter
    def run_jobs(self, value):
        if value is not None:
            if not isinstance(value, RunJobCollection):
                raise TypeError(
                    'Attribute "run_jobs" must have type '
                    'tmlib.workflow.jobs.RunJobCollection'
                )
            if len(self.tasks) == 0:
                if self.requires_init:
                    raise WorkflowTransitionError(
                        'Attempt to set "run" jobs before "init" phase.'
                    )
                self.tasks.append(value)
            elif len(self.tasks) == 1:
                self.tasks.append(value)
            else:
                if self.requires_init:
                    self.tasks[1] = value
                else:
                    self.tasks[0] = value

    @property
    def collect_job(self):
        '''tmlib.workflow.jobs.CollectJob: job for the "collect" phase'''
        try:
            if self.requires_init:
                return self.tasks[2]
            else:
                return self.tasks[1]
        except IndexError:
            raise WorkflowTransitionError(
                'Workflow step "%s" doesn\'t have a "collect" job.' % self.name
            )

    @collect_job.setter
    def collect_job(self, value):
        if value is not None:
            if not isinstance(value, CollectJob):
                raise TypeError(
                    'Attribute "collect_job" must have type '
                    'tmlib.workflow.jobs.CollectJob'
                )
            if len(self.tasks) == 0:
                raise WorkflowTransitionError(
                    'Attempt to set "collect" job before "init" and '
                    'and "run" phase.'
                )
            elif len(self.tasks) == 1:
                if self.requires_init:
                    raise WorkflowTransitionError(
                        'Attempt to set "collect" job before "run" phase.'
                    )
                self.tasks.append(value)
            elif len(self.tasks) == 2:
                self.tasks.append(value)
            else:
                if self.requires_init:
                    self.tasks[2] = value
                else:
                    self.tasks[1] = value

    @cached_property
    def _api_instance(self):
        logger.debug('load step interface "%s"', self.name)
        API = get_step_api(self.name)
        if getattr(self.description, 'extra_args', None):
            kwargs = dict()
            for name, value in self.description.extra_args.iterargitems():
                kwargs[name] = value
            api_instance = API(self.experiment_id, self.verbosity, **kwargs)
        else:
            api_instance = API(self.experiment_id, self.verbosity)
        return api_instance

    def create_init_job(self):
        '''Creates job for "init" phase.'''
        logger.info(
            'create job for "init" phase of step "%s"', self.name
        )
        self.init_job = self._api_instance.create_init_job(
            self.submission_id, self.user_name,
            self.description.batch_args

        )

    def initialize_run_jobs(self):
        '''Creates the job collection for "run" phase.'''
        self.run_jobs = self._api_instance.create_run_job_collection(
            self.submission_id
        )

    def create_run_jobs(self):
        '''Creates the jobs for "run" phase based on descriptions
        created by previous "init" phase.
        '''
        logger.info(
            'create jobs for "run" phase of step "%s"', self.name
        )
        batches = self._api_instance.get_batches_from_files()

        # TODO: check for required inputs in init phase
        # required_inputs = self._api_instance.list_input_files(batches)
        # # TODO: also check for existance of database entries
        # if not all([os.path.exists(i) for i in required_inputs]):
        #     logger.error('required inputs were not generated')
        #     raise WorkflowTransitionError(
        #         'Inputs for step "%s" do not exist.' % self.name
        #     )

        logger.info(
            'allocated time for "run" jobs: %s',
            self.description.submission_args.duration
        )
        logger.info(
            'allocated memory for "run" jobs: %d MB',
            self.description.submission_args.memory
        )
        logger.info(
            'allocated cores for "run" jobs: %d',
            self.description.submission_args.cores
        )
        self.run_jobs = self._api_instance.create_run_jobs(
            self.submission_id, self.user_name, self.run_jobs, batches['run'],
            duration=self.description.submission_args.duration,
            memory=self.description.submission_args.memory,
            cores=self.description.submission_args.cores
        )

    def create_collect_job(self):
        '''Creates job for "collect" phase based on descriptions
        created by previous "init" phase.
        '''
        self.collect_job = self._api_instance.create_collect_job(
            self.submission_id, self.user_name
        )

    def next(self, done):
        '''Progresses to the next phase.

        Parameters
        ----------
        done: int
            zero-based index of the last processed phase

        Returns
        -------
        gc3libs.Run.State
        '''
        if self.requires_init:
            if done == 0:
                self.create_run_jobs()
        return super(WorkflowStep, self).next(done)


class WorkflowStage(State):

    '''Base class for `TissueMAPS` workflow stages. A *workflow stage* is
    composed of one or more *workflow steps* that together comprise a logical
    computational unit.'''

    def __init__(self, name, experiment_id, verbosity, submission_id, user_name,
                 description):
        '''
        Parameters
        ----------
        name: str
            name of the stage
        experiment_id: int
            ID of the processed experiment
        verbosity: int
            logging verbosity index
        submission_id: int
            ID of the corresponding submission
        user_name: str
            name of the submitting user
        description: tmlib.tmaps.description.WorkflowStageDescription
            description of the stage

        Raises
        ------
        TypeError
            when `description` doesn't have type
            :py:class:`tmlib.workflow.tmaps.description.WorkflowStageDescription`
        '''
        self.name = name
        self.experiment_id = experiment_id
        self.verbosity = verbosity
        self.submission_id = submission_id
        self.user_name = user_name
        if not isinstance(description, WorkflowStageDescription):
            raise TypeError(
                'Argument "description" must have type '
                'tmlib.tmaps.description.WorkflowStageDescription'
            )
        self.description = description
        self.tasks = self._create_steps()

    def _create_steps(self):
        '''Creates all steps for this stage.

        Returns
        -------
        List[tmlib.workflow.WorkflowStep]
            workflow steps

        Note
        ----
        The steps don't have any jobs yet. They will later be added
        dynamically at runtime.
        '''
        workflow_steps = list()
        for step_description in self.description.steps:
            workflow_steps.append(
                WorkflowStep(
                    name=step_description.name,
                    experiment_id=self.experiment_id,
                    verbosity=self.verbosity,
                    submission_id=self.submission_id,
                    user_name=self.user_name,
                    description=step_description
                )
            )
        return workflow_steps

    @property
    def n_steps(self):
        '''int: number of steps in the stage'''
        return len(self.description.steps)


class SequentialWorkflowStage(SequentialTaskCollection, WorkflowStage, State):

    '''A *workflow stage* whose *steps* should be processed sequentially.
    The number of jobs is generally only known for the first step of the stage,
    but unknown for the subsequent steps, since their input depends on the
    output of the previous step. Subsequent steps are thus build
    dynamically upon transition from one step to the next.
    '''

    def __init__(self, name, experiment_id, verbosity,
                 submission_id, user_name, description=None, waiting_time=0):
        '''
        Parameters
        ----------
        name: str
            name of the stage
        experiment_id: int
            ID of the processed experiment
        verbosity: int
            logging verbosity index
        submission_id: int
            ID of the corresponding submission
        user_name: str
            name of the submitting user
        description: tmlib.tmaps.description.WorkflowStageDescription, optional
            description of the stage (default: ``None``)
        waiting_time: int, optional
            time in seconds that should be waited upon transition from one
            stage to the other to avoid issues related to network file systems
            (default: ``0``)
        '''
        SequentialTaskCollection.__init__(
            self, tasks=None, jobname='%s' % name
        )
        WorkflowStage.__init__(
            self, name=name, experiment_id=experiment_id, verbosity=verbosity,
            submission_id=submission_id, description=description,
            user_name=user_name
        )
        self.waiting_time = waiting_time

    def update_step(self, index):
        '''Updates the indexed step, i.e. creates new jobs for it.

        Parameters
        ----------
        index: int
            index for the list of `tasks` (steps)
        '''
        logger.debug('create job descriptions for next step')
        self.tasks[index].create_init_job()

    def next(self, done):
        '''Progresses to next step.

        Parameters
        ----------
        done: int
            zero-based index of the last processed step

        Returns
        -------
        gc3libs.Run.State
        '''
        logger.debug(
            'state of %s: %s',
            self.__class__.__name__, self.execution.state
        )
        # Implement StopOnError behavior: set the state of the task collection
        # to the state of the last processed task.
        self.execution.returncode = self.tasks[done].execution.returncode
        if self.execution.returncode != 0:
            # Stop the entire collection in case the last task "failed".
            # We only stop the workflow, so that the workflow could in principle
            # be resumed later.
            return gc3libs.Run.State.STOPPED
        if self.is_stopped:
            return gc3libs.Run.State.STOPPED
        elif self.is_terminated:
            return gc3libs.Run.State.TERMINATED
        logger.info('step "%s" is done', self.description.steps[done].name)
        if done+1 < self.n_steps:
            if self.waiting_time > 0:
                logger.info('waiting ...')
                logger.debug('wait %d seconds', self.waiting_time)
                time.sleep(self.waiting_time)
            try:
                next_step_name = self.description.steps[done+1].name
                logger.info(
                    'transit to next step ({0} of {1}): "{2}"'.format(
                        done+2, self.n_steps, next_step_name
                    )
                )
                self.update_step(done+1)
                return gc3libs.Run.State.RUNNING
            except Exception as error:
                exc_type, exc_value, exc_traceback = sys.exc_info()
                logger.error('transition to next stage failed: %s', error)
                tb = traceback.extract_tb(exc_traceback)[-1]
                logger.error('error in "%s" line %d', tb[0], tb[1])
                tb_string = ''
                for tb in traceback.format_tb(exc_traceback):
                    tb_string += '\n'
                    tb_string += tb
                tb_string += '\n'
                logger.debug('error traceback: %s', tb_string)
                logger.info('stopping stage "%s"', self.jobname)
                self.execution.state = gc3libs.Run.State.STOPPED
                raise
        else:
            return gc3libs.Run.State.TERMINATED


class ParallelWorkflowStage(WorkflowStage, ParallelTaskCollection, State):

    '''A *workflow stage* whose *workflow steps* should be processed at once
    in parallel. The number of jobs must thus be known for each step in advance.
    '''

    def __init__(self, name, experiment_id, verbosity, submission_id, user_name,
                 description=None):
        '''
        Parameters
        ----------
        name: str
            name of the stage
        experiment_id: int
            ID of the processed experiment
        verbosity: int
            logging verbosity index
        submission_id: int
            ID of the corresponding submission
        user_name: str
            name of the submitting user
        description: tmlib.tmaps.description.WorkflowStageDescription, optional
            description of the stage (default: ``None``)
        '''
        ParallelTaskCollection.__init__(
            self, tasks=None, jobname='%s' % name
        )
        WorkflowStage.__init__(
            self, name=name, experiment_id=experiment_id, verbosity=verbosity,
            submission_id=submission_id, user_name=user_name,
            description=description
        )

    def add(self, step):
        '''Adds a step.

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
                'tmlib.tmaps.workflow.WorkflowStep'
            )
        super(ParallelWorkflowStage, self).add(step)

    def _update_all_steps(self):
        for index, step_description in enumerate(self.description.steps):
            self.self.tasks[index].create_init_job()


class Workflow(SequentialTaskCollection, State):

    '''A *workflow* represents a computational pipeline that processes a
    sequence of *workflow stages* on a cluster.
    '''

    def __init__(self, experiment_id, verbosity, submission_id, user_name,
                 description, waiting_time=0):
        '''
        Parameters
        ----------
        experiment_id: int
            ID of processed experiment
        verbosity: int
            logging verbosity index
        submission_id: int
            ID of the corresponding submission
        user_name: str
            name of the submitting user
        description: tmlib.tmaps.description.WorkflowDescription
            description of the workflow
        waiting_time: int, optional
            time in seconds that should be waited upon transition from one
            stage to the other to avoid issues related to network file systems
            (default: ``0``)

        Note
        ----
        *Inactive* workflow stages/steps will not be ignored.

        See also
        --------
        :py:class:`tmlib.workflow.WorkflowStage`
        '''
        self.experiment_id = experiment_id
        self.verbosity = verbosity
        self.waiting_time = waiting_time
        self.submission_id = submission_id
        self.user_name = user_name
        self.update_description(description)
        with tmlib.models.utils.MainSession() as session:
            experiment = session.query(tmlib.models.ExperimentReference).\
                get(self.experiment_id)
            super(Workflow, self).__init__(tasks=None, jobname=experiment.name)
        self._current_task = 0
        self.tasks = self._create_stages()
        # Update the first stage and its first step to start the workflow
        self.update_stage(0)

    @assert_type(description='tmlib.workflow.description.WorkflowDescription')
    def update_description(self, description):
        '''Updates the workflow description, which will be used to dynamically
        build `stages` upon processing.

        Parameters
        ----------
        description: tmlib.tmaps.description.WorkflowDescription
            description of the workflow

        Raises
        ------
        TypeError
            when `description` doesn't have type
            :py:class:`tmlib.tmaps.description.WorkflowDescription`

        '''
        logger.info('update workflow description')
        self.description = copy.deepcopy(description)
        self.description.stages = list()
        for stage in description.stages:
            if stage.active:
                steps_to_process = list()
                for step in stage.steps:
                    if step.active:
                        steps_to_process.append(step)
                    else:
                        logger.debug('ignore inactive step "%s"', step.name)
                stage.steps = steps_to_process
                self.description.stages.append(stage)
            else:
                logger.debug('ignore inactive stage "%s"', stage.name)

    def _create_stages(self):
        '''Creates all stages for this workflow.

        Returns
        -------
        List[tmlib.workflow.WorkflowStage]
            workflow stages
        '''
        workflow_stages = list()
        for stage_desc in self.description.stages:
            stage = self._add_stage(stage_desc)
            workflow_stages.append(stage)
        return workflow_stages

    def _add_stage(self, description):
        '''Adds a new stage to the tasks list.

        Parameters
        ----------
        description: tmlib.workflow.description.WorkflowStageDescription
            description of the stage

        Returns
        -------
        tmlib.workflow.WorkflowStage
        '''
        if description.mode == 'sequential':
            logger.debug('build sequential workflow stage')
            return SequentialWorkflowStage(
                name=description.name,
                experiment_id=self.experiment_id,
                verbosity=self.verbosity,
                submission_id=self.submission_id,
                user_name=self.user_name,
                description=description,
                waiting_time=self.waiting_time
            )
        elif description.mode == 'parallel':
            logger.debug('build parallel workflow stage')
            return ParallelWorkflowStage(
                name=description.name,
                experiment_id=self.experiment_id,
                verbosity=self.verbosity,
                submission_id=self.submission_id,
                user_name=self.user_name,
                description=description
            )

    @property
    def n_stages(self):
        '''int: total number of active stages'''
        return len(self.description.stages)

    def update_stage(self, index):
        '''Updates the indexed stage, i.e. creates new jobs for each step of
        the stage.

        Parameters
        ----------
        index: int
            index for the list of `tasks` (stages)
        '''
        stage_desc = self.description.stages[index]
        logger.info('update stage #%d: %s', index, stage_desc.name)
        if index > len(self.tasks) - 1:
            stage = self._add_stage(stage_desc)
            self.tasks.append(stage)
        if stage_desc.mode == 'sequential':
            self.tasks[index].update_step(0)
        else:
            self.tasks[index]._update_all_steps()

    def next(self, done):
        '''Progresses to next stage.

        Parameters
        ----------
        done: int
            zero-based index of the last processed stage

        Returns
        -------
        gc3libs.Run.State
        '''
        logger.debug(
            'state of %s: %s',
            self.__class__.__name__, self.execution.state
        )
        # Implement StopOnError behavior: set the state of the task collection
        # to the state of the last processed task.
        self.execution.returncode = self.tasks[done].execution.returncode
        if self.execution.returncode != 0:
            return gc3libs.Run.State.STOPPED
        if self.is_stopped:
            return gc3libs.Run.State.STOPPED
        elif self.is_terminated:
            return gc3libs.Run.State.TERMINATED
        logger.info('stage "%s" is done', self.description.stages[done].name)
        if done+1 < self.n_stages:
            if self.waiting_time > 0:
                logger.info('waiting ...')
                logger.debug('wait %d seconds', self.waiting_time)
                time.sleep(self.waiting_time)
            try:
                next_stage_name = self.description.stages[done+1].name
                logger.info(
                    'transit to next stage ({0} of {1}): "{2}"'.format(
                        done+2, self.n_stages, next_stage_name
                    )
                )
                self.update_stage(done+1)
                return gc3libs.Run.State.RUNNING
            except Exception as error:
                logger.error('transition to next stage failed: %s', error)
                exc_type, exc_value, exc_traceback = sys.exc_info()
                tb = traceback.extract_tb(exc_traceback)[-1]
                logger.error('error in "%s" line %d', tb[0], tb[1])
                tb_string = str()
                for tb in traceback.format_tb(exc_traceback):
                    tb_string += '\n'
                    tb_string += tb  # TODO
                tb_string += '\n'
                logger.debug('error traceback: %s', tb_string)
                logger.info('stopping workflow "%s"', self.jobname)
                self.execution.state = gc3libs.Run.State.STOPPED
                raise
        else:
            return gc3libs.Run.State.TERMINATED
