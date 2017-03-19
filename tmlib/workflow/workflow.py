# TmLibrary - TissueMAPS library for distibuted image analysis routines.
# Copyright (C) 2016  Markus D. Herrmann, University of Zurich and Robin Hafen
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
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
    step within a larger workflow.
    '''

    def __init__(self, name, experiment_id, verbosity, submission_id, user_name,
            description):
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

        See also
        --------
        :class:`tmlib.workflow.description.WorkflowStepDescription`
        '''
        super(WorkflowStep, self).__init__(tasks=[], jobname=name)
        self.name = name
        self.experiment_id = experiment_id
        self.verbosity = verbosity
        self.submission_id = submission_id
        self.user_name = user_name
        self.description = description
        self._current_task = 0

    def initialize(self):
        '''Initializes the step, i.e. generates the jobs for the different
        phases.
        '''
        self.create_init_job()
        self.create_run_job_collection()
        if self._api_instance.has_collect_phase:
            self.create_collect_job()

    @property
    def init_job(self):
        '''tmlib.workflow.jobs.InitJob: job for the "init" phase'''
        try:
            return self.tasks[0]
        except IndexError:
            raise WorkflowTransitionError(
                'Workflow step "%s" doesn\'t have an "init" job.' % self.name
            )

    @init_job.setter
    def init_job(self, value):
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
            return self.tasks[1]
        except IndexError:
            raise WorkflowTransitionError(
                'Workflow step "%s" doesn\'t have any "run" jobs.' % self.name
            )

    @run_jobs.setter
    def run_jobs(self, value):
        if not isinstance(value, RunJobCollection):
            raise TypeError(
                'Attribute "run_jobs" must have type '
                'tmlib.workflow.jobs.RunJobCollection'
            )
        if len(self.tasks) == 0:
            raise WorkflowTransitionError(
                'Attempt to set "run" jobs before "init" phase.'
            )
        elif len(self.tasks) == 1:
            self.tasks.append(value)
        else:
            self.tasks[1] = value

    @property
    def collect_job(self):
        '''tmlib.workflow.jobs.CollectJob: job for the "collect" phase'''
        try:
            return self.tasks[2]
        except IndexError:
            raise WorkflowTransitionError(
                'Workflow step "%s" doesn\'t have a "collect" job.' % self.name
            )

    @collect_job.setter
    def collect_job(self, value):
        if not isinstance(value, CollectJob):
            raise TypeError(
                'Attribute "collect_job" must have type '
                'tmlib.workflow.jobs.CollectJob'
            )
        if len(self.tasks) == 0 or len(self.tasks) == 1:
            raise WorkflowTransitionError(
                'Attempt to set "collect" job before "run" phase.'
            )
        elif len(self.tasks) == 2:
            self.tasks.append(value)
        else:
            self.tasks[2] = value

    @cached_property
    def _api_instance(self):
        logger.debug('load step interface "%s"', self.name)
        API = get_step_api(self.name)
        return API(self.experiment_id)

    def create_init_job(self):
        '''Creates the job for "init" phase.'''
        logger.info('create job for "init" phase of step "%s"', self.name)
        self.init_job = self._api_instance.create_init_job(
            self.submission_id, self.user_name, self.description.batch_args,
            self.verbosity
        )

    def create_run_job_collection(self):
        '''Creates the job collection for "run" phase.'''
        self.run_jobs = self._api_instance.create_run_job_collection(
            self.submission_id
        )

    def create_run_jobs(self):
        '''Creates the individual jobs for the "run" phase based on descriptions
        created during the "init" phase.
        '''
        logger.info('create jobs for "run" phase of step "%s"', self.name)
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
            self.submission_id, self.user_name, self.run_jobs,
            self.verbosity,
            duration=self.description.submission_args.duration,
            memory=self.description.submission_args.memory,
            cores=self.description.submission_args.cores
        )

    def create_collect_job(self):
        '''Creates the job for "collect" phase based on descriptions
        created during the "init" phase.
        '''
        self.collect_job = self._api_instance.create_collect_job(
            self.submission_id, self.user_name, self.verbosity
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
        self.execution.returncode = self.tasks[done].execution.returncode
        if self.execution.returncode != 0:
            return gc3libs.Run.State.TERMINATED
        elif self.is_terminated:
            return gc3libs.Run.State.TERMINATED
        if done == 0:
            # The collection of jobs for the "run" phase has already been
            # created, but it must now be populated with the individual jobs.
            # The knowledge required to create the jobs was not available
            # prior to the "init" phase.
            self.create_run_jobs()
        return super(WorkflowStep, self).next(done)


class WorkflowStage(State):

    '''Base class for `TissueMAPS` workflow stages. A *workflow stage* is
    composed of one or more *workflow steps*, which together comprise an
    abstract computational task.
    '''

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
            when `description` doesn't have the correct type

        See also
        --------
        :class:`tmlib.workflow.description.WorkflowStageDescription`
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
        self.tasks[index].description = self.description.steps[index]
        self.tasks[index].initialize()

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
        '''Adds a `step`.

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
            self.tasks[index].description = step_description
            self.tasks[index].initialize()


class Workflow(SequentialTaskCollection, State):

    '''A *workflow* represents a computational pipeline that gets dynamically
    assembled from individual *stages* based on a user provided description.
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
            stage; required with certain network file systems settings
            (default: ``0``)

        Warning
        -------
        *Inactive* workflow stages/steps will be ignored.

        See also
        --------
        :class:`tmlib.workflow.description.WorkflowDescription`
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
        '''Updates the workflow description by removing *inactive* stages/steps
        from the description that will ultimately be used to dynamically
        build `stages` upon processing.

        Parameters
        ----------
        description: tmlib.tmaps.description.WorkflowDescription
            description of the workflow

        Raises
        ------
        TypeError
            when `description` doesn't have type
            :class:`WorkflowDescription <tmlib.workflow.description.WorkflowDescription>`

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
        for stage_description in self.description.stages:
            stage = self._add_stage(stage_description)
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
        '''Updates the indexed stage, i.e. creates the individual
        computational jobs for each step of the stage.

        Parameters
        ----------
        index: int
            index for the list of `tasks` (stages)
        '''
        stage_description = self.description.stages[index]
        logger.info('update stage #%d: %s', index, stage_description.name)
        if index > len(self.tasks) - 1:
            stage = self._add_stage(stage_description)
            self.tasks.append(stage)
        self.tasks[index].description = stage_description
        if stage_description.mode == 'sequential':
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
                    tb_string += tb
                tb_string += '\n'
                logger.debug('error traceback: %s', tb_string)
                logger.info('stopping workflow "%s"', self.jobname)
                self.execution.state = gc3libs.Run.State.STOPPED
                raise
        else:
            return gc3libs.Run.State.TERMINATED
