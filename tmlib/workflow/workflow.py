# TmLibrary - TissueMAPS library for distibuted image analysis routines.
# Copyright (C) 2016  Markus D. Herrmann, University of Zurich and Robin Hafen
# Copyright (C) 2018  University of Zurich
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
import gc3libs
from cached_property import cached_property
from gc3libs.workflow import (
    AbortOnError, SequentialTaskCollection, ParallelTaskCollection
)
from gc3libs.persistence.sql import IdFactory, IntId

import tmlib.models
from tmlib.utils import assert_type
from tmlib.workflow import get_step_api
from tmlib.workflow.description import WorkflowDescription
from tmlib.workflow.description import WorkflowStageDescription
from tmlib.errors import WorkflowTransitionError
from tmlib.readers import YamlReader
from tmlib.workflow.jobs import (
    InitJob, CollectJob, RunPhase, InitPhase, CollectPhase
)

logger = logging.getLogger(__name__)

_idfactory = IdFactory(id_class=IntId)


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
            parent_id, description):
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
        parent_id: int
            ID of the parent
            :class:`WorkflowStage <tmlib.workflow.workflow.WorkflowPhase>`
        description: tmlib.tmaps.description.WorkflowStepDescription
            description of the step

        See also
        --------
        :class:`tmlib.workflow.description.WorkflowStepDescription`
        '''
        logger.debug('instantiate step "%s"', name)
        super(WorkflowStep, self).__init__(tasks=[], jobname=name)
        self.name = name
        self.experiment_id = experiment_id
        self.verbosity = verbosity
        self.submission_id = submission_id
        self.user_name = user_name
        self.parent_id = parent_id
        self.persistent_id = _idfactory.new(self)
        self.description = description
        self._current_task = 0

    def initialize(self):
        '''Initializes the step, i.e. generates the jobs for the different
        phases.
        '''
        logger.info('initialize step "%s"', self.name)
        self.tasks = []
        self._create_init_phase()
        self._update_init_phase()
        self._create_run_phase()
        if self._api_instance.has_collect_phase:
            self._create_collect_phase()
            self._update_collect_phase()

    @property
    def init_phase(self):
        '''tmlib.workflow.jobs.InitJob: collection of job for the "init" phase
        '''
        try:
            return self.tasks[0]
        except IndexError:
            raise WorkflowTransitionError(
                'Workflow step "%s" doesn\'t have an "init" phase.' % self.name
            )

    @init_phase.setter
    def init_phase(self, value):
        if not isinstance(value, InitPhase):
            raise TypeError(
                'Attribute "init_phase" must have type '
                'tmlib.workflow.jobs.InitPhase'
            )
        if len(self.tasks) == 0:
            self.tasks.append(value)
        else:
            self.tasks[0] = value

    @property
    def run_phase(self):
        '''tmlib.workflow.jobs.RunPhase: collection of jobs for the
        "run" phase
        '''
        try:
            return self.tasks[1]
        except IndexError:
            raise WorkflowTransitionError(
                'Workflow step "%s" doesn\'t have a "run" phase.' % self.name
            )

    @run_phase.setter
    def run_phase(self, value):
        if not isinstance(value, RunPhase):
            raise TypeError(
                'Attribute "run_jobs" must have type '
                'tmlib.workflow.jobs.RunPhase'
            )
        if len(self.tasks) == 0:
            raise WorkflowTransitionError(
                'Attempt to set "run" phase before "init" phase.'
            )
        elif len(self.tasks) == 1:
            self.tasks.append(value)
        else:
            self.tasks[1] = value

    @property
    def collect_phase(self):
        '''tmlib.workflow.jobs.CollectPhase: collection of jobs for "collect"
        phase
        '''
        try:
            return self.tasks[2]
        except IndexError:
            raise WorkflowTransitionError(
                'Workflow step "%s" doesn\'t have a "collect" phase.' % self.name
            )

    @collect_phase.setter
    def collect_phase(self, value):
        if not isinstance(value, CollectPhase):
            raise TypeError(
                'Attribute "collect_phase" must have type '
                'tmlib.workflow.jobs.CollectPhase'
            )
        if len(self.tasks) == 0 or len(self.tasks) == 1:
            raise WorkflowTransitionError(
                'Attempt to set "collect" phase before "run" phase.'
            )
        elif len(self.tasks) == 2:
            self.tasks.append(value)
        else:
            self.tasks[2] = value

    @cached_property
    def _api_instance(self):
        logger.debug('load API for step "%s"', self.name)
        API = get_step_api(self.name)
        return API(self.experiment_id)

    def _create_init_phase(self):
        '''Creates the job collection for "init" phase.'''
        logger.debug(
            'create job collection for "init" phase of step "%s"', self.name
        )
        self.init_phase = self._api_instance.create_init_phase(
            self.submission_id, self.persistent_id
        )

    def _update_init_phase(self):
        '''Creates the job for "init" phase.'''
        logger.info('create job for "init" phase of step "%s"', self.name)
        self.init_phase = self._api_instance.create_init_job(
            self.user_name, self.init_phase, self.description.batch_args,
            self.verbosity
        )

    def _create_run_phase(self):
        '''Creates the job collection for "run" phase.'''
        logger.debug(
            'create job collection for "run" phase of step "%s"', self.name
        )
        self.run_phase = self._api_instance.create_run_phase(
            self.submission_id, self.persistent_id
        )

    def _update_run_phase(self):
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
        self.run_phase = self._api_instance.create_run_jobs(
            self.user_name, self.run_phase, self.verbosity,
            duration=self.description.submission_args.duration,
            memory=self.description.submission_args.memory,
            cores=self.description.submission_args.cores
        )

    def _create_collect_phase(self):
        '''Creates the job collection for "collect" phase.'''
        logger.debug(
            'create job collection for "collect" phase of step "%s"', self.name
        )
        self.collect_phase = self._api_instance.create_collect_phase(
            self.submission_id, self.persistent_id
        )

    def _update_collect_phase(self):
        '''Creates the job for "collect" phase based on descriptions
        created during the "init" phase.
        '''
        logger.info('create job for "collect" phase of step "%s"', self.name)
        self.collect_phase = self._api_instance.create_collect_job(
            self.user_name, self.collect_phase, self.verbosity
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
        logger.debug(
            'state of %s: %s',
            self.__class__.__name__, self.execution.state
        )
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
            self._update_run_phase()
        logger.info('transition to next phase of step "%s"', self.name)
        return super(WorkflowStep, self).next(done)


class WorkflowStage(State):

    '''Base class for `TissueMAPS` workflow stages. A *workflow stage* is
    composed of one or more *workflow steps*, which together comprise an
    abstract computational task.
    '''

    def __init__(self, name, experiment_id, verbosity, submission_id, user_name,
                 parent_id, description):
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
        parent_id: int
            ID of the parent
            :class:`Workflow <tmlib.workflow.workflow.Workflow>`
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
        logger.debug('instantiate workflow stage "%s"', name)
        self.name = name
        self.experiment_id = experiment_id
        self.verbosity = verbosity
        self.submission_id = submission_id
        self.user_name = user_name
        self.parent_id = parent_id
        if not isinstance(description, WorkflowStageDescription):
            raise TypeError(
                'Argument "description" must have type '
                'tmlib.tmaps.description.WorkflowStageDescription'
            )
        self.description = description
        self.persistent_id = _idfactory.new(self)
        self._add_steps()

    def _add_steps(self):
        logger.debug('create steps of stage "%s"', self.name)
        for step_description in self.description.steps:
            step = self._create_step(step_description)
            self.tasks.append(step)

    def _create_step(self, description):
        logger.debug(
            'create step "%s" of stage "%s"', description.name, self.name
        )
        return WorkflowStep(
            name=description.name,
            experiment_id=self.experiment_id,
            verbosity=self.verbosity,
            submission_id=self.submission_id,
            user_name=self.user_name,
            parent_id=self.persistent_id,
            description=description
        )

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
                 submission_id, user_name, parent_id, description=None,
                 waiting_time=0):
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
        parent_id: int
            ID of the parent
            :class:`Workflow <tmlib.workflow.workflow.Workflow>`
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
            user_name=user_name, parent_id=parent_id
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
        # Implement TerminateOnError behavior: set the state of the task
        # collection to the state of the last processed task.
        self.execution.returncode = self.tasks[done].execution.returncode
        if self.execution.returncode != 0:
            return gc3libs.Run.State.TERMINATED
        if self.is_stopped:
            return gc3libs.Run.State.TERMINATED
        elif self.is_terminated:
            return gc3libs.Run.State.TERMINATED
        logger.info(
            'step "%s" of stage "%s" is done',
            self.description.steps[done].name, self.name
        )
        if done+1 < self.n_steps:
            if self.waiting_time > 0:
                logger.info('waiting ...')
                logger.debug('wait %d seconds', self.waiting_time)
                time.sleep(self.waiting_time)
            try:
                next_step_name = self.description.steps[done+1].name
                logger.info(
                    'transit to step "{0}" of stage "{1}" ({2} of {3})'.format(
                        next_step_name, self.name, done+2, self.n_steps
                    )
                )
                self.update_step(done+1)
                return gc3libs.Run.State.RUNNING
            except Exception as error:
                logger.error(
                    'workflow stage "%s":'
                    ' transition to step "%s" failed -- terminating!',
                    self.name, error)
                logger.debug(
                    'workflow stage "%s": detailed Python traceback follows',
                    self.name, exc_info=True)
                self.execution.state = gc3libs.Run.State.TERMINATED
                raise
        else:
            return gc3libs.Run.State.TERMINATED


class ParallelWorkflowStage(WorkflowStage, ParallelTaskCollection, State):

    '''A *workflow stage* whose *workflow steps* should be processed at once
    in parallel. The number of jobs must thus be known for each step in advance.
    '''

    def __init__(self, name, experiment_id, verbosity, submission_id, user_name,
                 parent_id, description=None):
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
        parent_id: int
            ID of the parent
            :class:`Workflow <tmlib.workflow.workflow.Workflow>`
        description: tmlib.tmaps.description.WorkflowStageDescription, optional
            description of the stage (default: ``None``)
        '''
        ParallelTaskCollection.__init__(
            self, tasks=None, jobname='%s' % name
        )
        WorkflowStage.__init__(
            self, name=name, experiment_id=experiment_id, verbosity=verbosity,
            submission_id=submission_id, user_name=user_name,
            parent_id=parent_id, description=description
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
        with tmlib.models.utils.MainSession() as session:
            experiment = session.query(tmlib.models.ExperimentReference).\
                get(self.experiment_id)
            self.name = experiment.name
            super(Workflow, self).__init__(tasks=None, jobname=self.name)
        self.update_description(description)
        self.parent_id = None
        self.persistent_id = _idfactory.new(self)
        self._current_task = 0
        self._add_stages()
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
        logger.info('update description of workflow "%s"', self.name)
        self.description = copy.deepcopy(description)
        self.description.stages = list()
        for stage in description.stages:
            if stage.active:
                steps_to_process = list()
                for step in stage.steps:
                    if step.active:
                        steps_to_process.append(step)
                    else:
                        logger.debug(
                            'ignore inactive step "%s" of workflow "%s"',
                            step.name, self.name
                        )
                stage.steps = steps_to_process
                self.description.stages.append(stage)
            else:
                logger.debug(
                    'ignore inactive stage "%s" of workflow "%s"',
                    stage.name, self.name
                )

    def _add_stages(self):
        logger.debug('create stages of workflow "%s"', self.name)
        for stage_description in self.description.stages:
            stage = self._create_stage(stage_description)
            self.tasks.append(stage)

    def _create_stage(self, description):
        if description.mode == 'sequential':
            logger.debug(
                'create sequential stage "%s" of workflow "%s"',
                description.name, self.name
            )
            stage = SequentialWorkflowStage(
                name=description.name,
                experiment_id=self.experiment_id,
                verbosity=self.verbosity,
                submission_id=self.submission_id,
                user_name=self.user_name,
                parent_id=self.persistent_id,
                description=description,
                waiting_time=self.waiting_time
            )
        elif description.mode == 'parallel':
            logger.debug(
                'create parallel stage "%s" of workflow "%s"',
                description.name, self.name
            )
            stage = ParallelWorkflowStage(
                name=description.name,
                experiment_id=self.experiment_id,
                verbosity=self.verbosity,
                submission_id=self.submission_id,
                user_name=self.user_name,
                parent_id=self.persistent_id,
                description=description
            )
        return stage

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
        logger.info(
            'update stage "%s" (#%d) of workflow "%s"',
            stage_description.name, index, self.name
        )
        if index > len(self.tasks) - 1:
            stage = self._create_stage(stage_description)
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
        # Implement TerminateOnError behavior: set the state of the task
        # collection to the state of the last processed task.
        self.execution.returncode = self.tasks[done].execution.returncode
        if self.execution.returncode != 0:
            return gc3libs.Run.State.TERMINATED
        if self.is_stopped:
            return gc3libs.Run.State.TERMINATED
        elif self.is_terminated:
            return gc3libs.Run.State.TERMINATED
        logger.info(
            'stage "%s" of workflow "%s" is done',
            self.description.stages[done].name, self.name
        )
        if done+1 < self.n_stages:
            if self.waiting_time > 0:
                logger.info('waiting ...')
                logger.debug('wait %d seconds', self.waiting_time)
                time.sleep(self.waiting_time)
            try:
                next_stage_name = self.description.stages[done+1].name
                logger.info(
                    'transit to stage "{0}" of workflow "{1}" ({2} of {3})'.format(
                        next_stage_name, self.name, done+2, self.n_stages
                    )
                )
                self.update_stage(done+1)
                return gc3libs.Run.State.RUNNING
            except Exception as error:
                logger.error(
                    'workflow "%s":'
                    ' transition to next stage failed: %s -- terminating!',
                    self.name, error)
                logger.debug(
                    'workflow "%s": detailed Python traceback follows',
                    self.name, exc_info=True)
                self.execution.state = gc3libs.Run.State.TERMINATED
                raise
        else:
            return gc3libs.Run.State.TERMINATED
