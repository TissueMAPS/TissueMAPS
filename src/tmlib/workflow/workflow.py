import time
import os
import logging
import importlib
import sys
import traceback
from cached_property import cached_property
import gc3libs
from gc3libs.workflow import SequentialTaskCollection
from gc3libs.workflow import ParallelTaskCollection
from gc3libs.workflow import StopOnError, AbortOnError

import tmlib.models
from tmlib.workflow.description import WorkflowDescription
from tmlib.workflow.description import WorkflowStageDescription
from tmlib.errors import WorkflowTransitionError
from tmlib.readers import YamlReader
from tmlib.workflow.jobs import CollectJob
from tmlib.workflow.jobs import RunJobCollection
from tmlib.workflow.jobs import MultiRunJobCollection

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


def get_step_interface(step_name, experiment_id, verbosity, **kwargs):
    '''Gets the active programming interface for a `TissueMAPS` workflow step.

    Parameters
    ----------
    step_name: str
        name of the step whose interface should be returned
    experiment_id: int
        ID of the processed experiment
    verbosity: int
        logging level
    **kwargs: dict, optional
        additional keyword arguments that may have to be passed to the
        constructor of the step-specific implementation of the
        :py:class:` tmlib.workflow.cli.ClusterRoutines` abstract base class

    Returns
    -------
    tmlib.workflow.cli.ClusterRoutines
        step interface

    Raises
    ------
    ValueError
        when `step_name` is not a valid step name
    AttributeError
        when there is no step-specific `factory()` method available
    '''
    module_name = '%s.%s.api' % ('.'.join(__name__.split('.')[:-1]), step_name)
    try:
        module = importlib.import_module(module_name)
    except ImportError:
        raise ValueError('Unknown step "%s".' % step_name)
    try:
        factory = getattr(module, 'factory')
        return factory(experiment_id, verbosity, **kwargs)
    except AttributeError:
        raise AttributeError(
            'No factory method available for step "%s".', step_name
        )
    except:
        raise


def import_workflow_type_specific_module(workflow_type):
    '''Loads the module for an implemented workflow type.

    Parameters
    ----------
    workflow_type: str
        workflow type

    Returns
    -------
    module
        loaded module instance

    Raises
    ------
    ValueError
        when `workflow_type` is not known
    '''
    module_name = 'tmlib.workflow.%s' % workflow_type
    try:
        return importlib.import_module(module_name)
    except ImportError:
        raise ValueError('Unknown workflow type "%s".')


def workflow_description_factory(workflow_type):
    '''Returns the implementation
    of the :py:class:`tmlib.workflow.tmaps.description.WorkflowDescription`
    abstract base class for the given workflow type.

    Parameters
    ----------
    workflow_type: str
        workflow type

    Returns
    -------
    tmlib.workflow.tmaps.description.WorkflowDescription
    '''
    module = import_workflow_type_specific_module(workflow_type)
    class_name = '%sWorkflowDescription' % workflow_type.capitalize()
    return getattr(module, class_name)


class WorkflowStep(AbortOnError, SequentialTaskCollection, State):

    '''A *workflow step* represents a collection of computational tasks
    that should be processed in parallel on a cluster, i.e. one parallelization
    step within a larger, more complex workflow.
    The number of jobs and the arguments for each job are known upon submission.
    '''

    def __init__(self, name, submission_id, run_jobs=None, collect_job=None):
        '''
        Parameters
        ----------
        name: str
            name of the step
        submission_id: int
            ID of the corresponding submission
        run_jobs: tmlib.jobs.RunJobCollection, optional
            jobs for the *run* phase that should be processed in parallel
            (default: ``None``)
        collect_job: tmlib.jobs.CollectJob, optional
            job for the *collect* phase that should be processed after
            `run_jobs` have terminated successfully (default: ``None``)
        '''
        self.name = name
        self.submission_id = submission_id
        tasks = list()
        self.run_jobs = run_jobs
        self.collect_job = collect_job
        super(WorkflowStep, self).__init__(tasks=tasks, jobname=name)

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

    def __init__(self, name, experiment_id, verbosity, submission_id,
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
                WorkflowStep(name=step.name, submission_id=self.submission_id)
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
        step_interface = get_step_interface(
            step_name, self.experiment_id, self.verbosity,
            **dict(step_description.args.variable_args)
        )

        # TODO: cleanup
        logger.debug('create batches')
        batches = step_interface.create_batches(
            step_description.args.variable_args
        )
        logger.debug('write batches to files')
        step_interface.write_batch_files(batches)
        required_inputs = step_interface.list_input_files(batches)
        # Check whether inputs of current step were generated by previous steps
        if not all([os.path.exists(i) for i in required_inputs]):
            logger.error('required inputs were not generated')
            raise WorkflowTransitionError(
                'inputs for step "%s" do not exist' % step_description.name
            )

        # # Store the expected outputs to be later able to check whether they
        # # were actually generated
        # self.expected_outputs.append(prog_instance.expected_outputs)
        self.expected_outputs = step_interface.list_output_files(batches)

        logger.info('allocated time: %s', step_description.duration)
        logger.info('allocated memory: %d GB', step_description.memory)
        logger.info('allocated cores: %d', step_description.cores)
        return step_interface.create_jobs(
            batches=batches,
            step=step,
            duration=step_description.duration,
            memory=step_description.memory,
            cores=step_description.cores
        )


class SequentialWorkflowStage(SequentialTaskCollection, WorkflowStage, State):

    '''A *workflow stage* whose *steps* should be processed sequentially.
    The number of jobs is generally only known for the first step of the stage,
    but unknown for the subsequent steps, since their input depends on the
    output of the previous step. Subsequent steps are thus build
    dynamically upon transition from one step to the next.
    '''

    def __init__(self, name, experiment_id, verbosity,
                 submission_id, description=None, waiting_time=0):
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
            submission_id=submission_id, description=description
        )
        self.waiting_time = waiting_time

    def _update_step(self, index):
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
                    'outputs of previous step do not exist'
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
                self._update_step(done+1)
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

    def __init__(self, name, experiment_id, verbosity, submission_id,
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
        description: tmlib.tmaps.description.WorkflowStageDescription, optional
            description of the stage (default: ``None``)
        '''
        ParallelTaskCollection.__init__(
            self, tasks=None, jobname='%s' % name
        )
        WorkflowStage.__init__(
            self, name=name, experiment_id=experiment_id, verbosity=verbosity,
            submission_id=submission_id, description=description
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

    def __init__(self, experiment_id, verbosity, submission_id,
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
        ValueError
            when `description` is not provided and cannot be retrieved from
            the user configuration file

        See also
        --------
        :py:class:`tmlib.cfg.UserConfiguration`
       '''
        # TODO: consider pre-building tasks and then later adding subtasks
        # (individual jobs) for more convenient monitoring
        self.experiment_id = experiment_id
        self.verbosity = verbosity
        self.waiting_time = waiting_time
        self.submission_id = submission_id
        with tmlib.models.utils.Session() as session:
            experiment = session.query(tmlib.models.Experiment).\
                get(self.experiment_id)
            super(Workflow, self).__init__(tasks=None, jobname=experiment.name)
            self.workflow_location = experiment.workflow_location
        if description is not None:
            if not isinstance(description, WorkflowDescription):
                raise TypeError(
                    'Argument "description" must have type '
                    'tmlib.tmaps.description.WorkflowDescription'
                )
            self.description = description
        else:
            self.description = self._read_description_from_file()
        self.start_stage = None
        self.start_step = None
        self.tasks = self._create_stages()
        # Update the first stage and its first step to start the workflow
        self._update_stage(0)

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
                        description=stage
                    )
                )
        return workflow_stages

    @property
    def start_stage(self):
        '''str: name of stage where workflow should be (re)started'''
        return self._start_stage

    @start_stage.setter
    def start_stage(self, value):
        if value is not None:
            if not isinstance(value, basestring):
                raise TypeError(
                    'Attribute "start_stage" must have type basestring.'
                )
            stage_names = [s.name for s in self.description.stages]
            if value not in stage_names:
                raise ValueError(
                    'Value of attribute "start_stage" can be '
                    'one of the following:\n"%s"' % '" or "'.join(stage_names)
                )
            self._update_stage(stage_names.index(value))
        self._start_stage = value

    @property
    def description_file(self):
        '''str: absolute path to workflow description file'''
        return os.path.join(
            self.workflow_location, 'workflow_description.yaml'
        )

    def _read_description_from_file(self):
        '''Reads description of workflow in YAML format from file.

        Returns
        -------
        tmlib.workflow.tmaps.description.WorkflowDescription
            description of the workflow

        Raises
        ------
        TypeError
            when description obtained from file is not a mapping
        KeyError
            when description obtained from file doesn't have key "type"
        '''
        with YamlReader(self.description_file) as f:
            description = f.read()
        if not isinstance(description, dict):
            raise TypeError('Description must be a mapping.')
        if 'type' not in description:
            raise KeyError('Description must have key "type".')
        workflow_description_class = workflow_description_factory(
            description['type']
        )
        return workflow_description_class(**description)

    @property
    def n_stages(self):
        '''int: total number of stages'''
        return len(self.description.stages)

    def _update_stage(self, index):
        '''Updates the indexed stage, i.e. creates new jobs for each step of
        the stage.

        Parameters
        ----------
        index: int
            index for the list of `tasks` (stages)
        '''
        stage = self.description.stages[index]
        if stage.mode == 'sequential':
            self.tasks[index]._update_step(0)
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
                self._update_stage(done+1)
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
