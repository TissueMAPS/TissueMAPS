import time
import os
import logging
import importlib
import sys
import traceback
import gc3libs
from gc3libs.workflow import SequentialTaskCollection
from gc3libs.workflow import ParallelTaskCollection
from gc3libs.workflow import AbortOnError

import tmlib.models
from tmlib.workflow.registry import get_step_api
from tmlib.workflow.description import WorkflowDescription
from tmlib.workflow.description import WorkflowStageDescription
from tmlib.errors import WorkflowTransitionError
from tmlib.readers import YamlReader
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
    The number of jobs and the arguments for each job are known upon submission.
    '''

    def __init__(self, name, submission_id, user_name, run_jobs=None, collect_job=None):
        '''
        Parameters
        ----------
        name: str
            name of the step
        submission_id: int
            ID of the corresponding submission
        user_name: str
            name of the submitting user
        run_jobs: tmlib.jobs.RunJobCollection, optional
            jobs for the *run* phase that should be processed in parallel
            (default: ``None``)
        collect_job: tmlib.jobs.CollectJob, optional
            job for the *collect* phase that should be processed after
            `run_jobs` have terminated successfully (default: ``None``)
        '''
        super(WorkflowStep, self).__init__(tasks=list(), jobname=name)
        self.name = name
        self.submission_id = submission_id
        self.user_name = user_name
        self.run_jobs = run_jobs
        self.collect_job = collect_job
        self._current_task = 0

    @property
    def run_jobs(self):
        '''tmlib.workflow.jobs.RunJobCollection: collection of run jobs'''
        try:
            return self.tasks[0]
        except IndexError:
            return None

    @run_jobs.setter
    def run_jobs(self, value):
        if value is not None:
            if not isinstance(value, RunJobCollection):
                raise TypeError(
                    'Attribute "run_jobs" must have type '
                    'tmlib.workflow.jobs.RunJobCollection'
                )
            if len(self.tasks) == 0:
                self.tasks.append(value)
            else:
                self.tasks[0] = value

    @property
    def collect_job(self):
        '''tmlib.workflow.jobs.CollectJob: individual collect job'''
        try:
            return self.tasks[1]
        except IndexError:
            return None

    @collect_job.setter
    def collect_job(self, value):
        if value is not None:
            if not isinstance(value, CollectJob):
                raise TypeError(
                    'Attribute "collect_job" must have type '
                    'tmlib.workflow.jobs.CollectJob'
                )
            if len(self.tasks) == 0:
                self.tasks.append(None)
                self.tasks.append(value)
            elif len(self.tasks) == 1:
                self.tasks.append(value)
            else:
                self.tasks[1] = value

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
        self.expected_outputs = None
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
        for step in self.description.steps:
            workflow_steps.append(
                WorkflowStep(
                    name=step.name,
                    submission_id=self.submission_id,
                    user_name=self.user_name
                )
            )
        return workflow_steps

    @property
    def n_steps(self):
        '''int: number of steps in the stage'''
        return len(self.description.steps)

    def create_jobs_for_next_step(self, step, step_description):
        '''Creates jobs for a given workflow step based on the provided
        description.

        Parameters
        ----------
        step: tmlib.workflow.WorkflowStep
            the step for which jobs should be created
        step_description: tmlib.workflow.description.WorkflowStepDescription
            description of the step

        Returns
        -------
        tmlib.tmaps.workflow.WorkflowStep
            step that should be processed next
        '''
        logger.info('create jobs for step "%s"', step_description.name)
        step_name = step_description.name
        logger.debug('load step interface "%s"', step_name)
        api_class = get_step_api(step_name)
        if getattr(step_description, 'extra_args', None):
            kwargs = dict()
            for name, value in step_description.extra_args.iterargitems():
                kwargs[name] = value
            api_instance = api_class(
                self.experiment_id, self.verbosity, **kwargs
            )
        else:
            api_instance = api_class(self.experiment_id, self.verbosity)
        logger.info('delete previous job output')
        api_instance.delete_previous_job_output()
        logger.info('create batches')
        batches = api_instance.create_batches(step_description.batch_args)
        logger.debug('write batches to files')
        api_instance.write_batch_files(batches)
        required_inputs = api_instance.list_input_files(batches)
        # Check whether inputs of current step were generated by previous steps
        if not all([os.path.exists(i) for i in required_inputs]):
            logger.error('required inputs were not generated')
            raise WorkflowTransitionError(
                'inputs for step "%s" do not exist' % step_description.name
            )

        # # Store the expected outputs to be later able to check whether they
        # # were actually generated
        # self.expected_outputs.append(prog_instance.expected_outputs)
        self.expected_outputs = api_instance.list_output_files(batches)
        logger.info(
            'allocated time: %s', step_description.submission_args.duration
        )
        logger.info(
            'allocated memory: %d MB', step_description.submission_args.memory
        )
        logger.info(
            'allocated cores: %d', step_description.submission_args.cores
        )
        job_ids = range(1, len(batches['run']) + 1)
        step.run_jobs = api_instance.create_run_jobs(
            self.submission_id,
            self.user_name,
            job_ids,
            duration=step_description.submission_args.duration,
            memory=step_description.submission_args.memory,
            cores=step_description.submission_args.cores
        )
        if 'collect' in batches:
            step.collect_job = api_instance.create_collect_job(
                self.submission_id,
                self.user_name
            )
        return step


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
        if index > 0:
            # NOTE: Checking the existence of files can be problematic,
            # because NFS may lie. We try to circumvent this by waiting upon
            # transition to the next step, but this not be sufficient.
            if not all([os.path.exists(f) for f in self.expected_outputs]):
                raise WorkflowTransitionError(
                    'outputs of previous step do not exist (submission: %d)'
                    % self.submission_id
                )
        logger.debug('create job descriptions for next step')
        self.tasks[index] = self.create_jobs_for_next_step(
            self.tasks[index], self.description.steps[index]
        )

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
                        done+1, self.n_steps, next_step_name
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
            self.tasks[index] = self.create_jobs_for_next_step(
                self.tasks[index], step_description
            )


class Workflow(SequentialTaskCollection, State):

    '''A *workflow* represents a computational pipeline that processes one
    *workflow stage* after another on a cluster.
    '''

    def __init__(self, experiment_id, verbosity, submission_id, user_name,
                 description=None, waiting_time=0):
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
        description: tmlib.tmaps.description.WorkflowDescription, optional
            description of the workflow (default: ``None``)
        waiting_time: int, optional
            time in seconds that should be waited upon transition from one
            stage to the other to avoid issues related to network file systems
            (default: ``0``)

        Note
        ----
        If `description` is not provided, there will be an attempt to obtain
        it from :py:attr:`tmlib.workflow.Workflow.description_file`.

        Raises
        ------
        TypeError
            when `description` doesn't have type
            :py:class:`tmlib.tmaps.description.WorkflowDescription`

        See also
        --------
        :py:class:`tmlib.cfg.UserConfiguration`
       '''
        self.experiment_id = experiment_id
        self.verbosity = verbosity
        self.waiting_time = waiting_time
        self.submission_id = submission_id
        self.user_name = user_name
        with tmlib.models.utils.Session() as session:
            experiment = session.query(tmlib.models.Experiment).\
                get(self.experiment_id)
            super(Workflow, self).__init__(tasks=None, jobname=experiment.name)
            self.workflow_location = experiment.workflow_location
        if not isinstance(description, WorkflowDescription):
             raise TypeError(
                 'Argument "description" must have type '
                 'tmlib.tmaps.description.WorkflowDescription'
             )
        self.description = description
        self._current_task = 0
        self.tasks = self._create_stages()
        # Update the first stage and its first step to start the workflow
        self.update_stage(0)

    def _create_stages(self):
        '''Creates all stages for this workflow.

        Returns
        -------
        List[tmlib.workflow.WorkflowStage]
            workflow stages
        '''
        workflow_stages = list()
        for stage in self.description.stages:
            if stage.mode == 'sequential':
                logger.debug('build sequential workflow stage')
                workflow_stages.append(
                    SequentialWorkflowStage(
                        name=stage.name,
                        experiment_id=self.experiment_id,
                        verbosity=self.verbosity,
                        submission_id=self.submission_id,
                        user_name=self.user_name,
                        description=stage,
                        waiting_time=self.waiting_time
                    )
                )
            elif stage.mode == 'parallel':
                logger.debug('build parallel workflow stage')
                workflow_stages.append(
                    ParallelWorkflowStage(
                        name=stage.name,
                        experiment_id=self.experiment_id,
                        verbosity=self.verbosity,
                        submission_id=self.submission_id,
                        user_name=self.user_name,
                        description=stage
                    )
                )
        return workflow_stages

    @property
    def n_stages(self):
        '''int: total number of stages'''
        return len(self.description.stages)

    def update_stage(self, index):
        '''Updates the indexed stage, i.e. creates new jobs for each step of
        the stage.

        Parameters
        ----------
        index: int
            index for the list of `tasks` (stages)
        '''
        stage = self.description.stages[index]
        if stage.mode == 'sequential':
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
                        done+1, self.n_stages, next_stage_name
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
