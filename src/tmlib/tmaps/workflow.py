import time
import logging
import importlib
from cached_property import cached_property
from abc import ABCMeta
from abc import abstractproperty
# from abc import abstractmethod
import gc3libs
from gc3libs import Run
from gc3libs import Application
# from gc3libs.workflow import RetryableTask
from gc3libs.workflow import SequentialTaskCollection
from gc3libs.workflow import ParallelTaskCollection
from gc3libs.workflow import StopOnError
from .description import WorkflowDescription
from .description import WorkflowStageDescription
from ..errors import WorkflowTransitionError
from ..utils import create_datetimestamp

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


class Job(Application):

    '''
    Abstract base class for a TissueMAPS job.

    Note
    ----
    Jobs can be constructed based on job descriptions, which persist on disk
    in form of JSON files.
    '''

    # TODO: inherit from RetryableTask(max_retries=1) and implement
    # re-submission logic by overwriting retry() method:
    # if exitcode != 0: don't resubmit
    # if any([re.search(r"FAILED", f) for f in stderr_files]): don't resubmit
    # if exitcode is None: resubmit

    __metaclass__ = ABCMeta

    def __init__(self, step_name, arguments, output_dir):
        '''
        Initialize an instance of class Job.

        Parameters
        ----------
        step_name: str
            name of the corresponding TissueMAPS workflow step
        arguments: List[str]
            command line arguments
        output_dir: str
            absolute path to the output directory, where log reports will
            be stored
        '''
        t = create_datetimestamp()
        self.step_name = step_name
        super(Job, self).__init__(
            jobname=self.name,
            arguments=arguments,
            output_dir=output_dir,
            inputs=[],
            outputs=[],
            stdout='%s_%s.out' % (self.name, t),
            stderr='%s_%s.err' % (self.name, t)
        )

    @abstractproperty
    def name(self):
        '''
        Returns
        -------
        str
            name of the job
        '''
        pass

    def retry(self):
        '''
        Decide whether the job should be retried.

        Returns
        -------
        bool
            whether job should be resubmitted
        '''
        # TODO
        return super(Job, self).retry()


class RunJob(Job):

    '''
    Class for TissueMAPS run jobs, which can be processed in parallel.
    '''

    def __init__(self, step_name, arguments, output_dir, job_id):
        '''
        Initialize an instance of class RunJob.

        Parameters
        ----------
        step_name: str
            name of the corresponding TissueMAPS workflow step
        arguments: List[str]
            command line arguments
        output_dir: str
            absolute path to the output directory, where log reports will
            be stored
        job_id: int
            one-based job identifier number
        '''
        self.job_id = job_id
        super(RunJob, self).__init__(
            step_name=step_name,
            arguments=arguments,
            output_dir=output_dir)

    @property
    def name(self):
        '''
        Returns
        -------
        str
            name of the job
        '''
        return '%s_run_%.6d' % (self.step_name, self.job_id)


class RunJobCollection(ParallelTaskCollection):

    '''
    Class for TissueMAPS run jobs based on a
    `gc3libs.workflow.ParallelTaskCollection`.
    '''

    def __init__(self, step_name):
        '''
        Initialize an instance of class RunJobCollection.

        Parameters
        ----------
        step_name: str
            name of the corresponding TissueMAPS workflow step
        '''
        self.step_name = step_name
        super(RunJobCollection, self).__init__(jobname='%s_run' % step_name)

    def add(self, job):
        '''
        Add a job to the collection.

        Parameters
        ----------
        job: tmlibs.tmaps.workflow.RunJob
            job that should be added

        Raises
        ------
        TypeError
            when `job` has wrong type
        '''
        if not isinstance(job, RunJob):
            raise TypeError(
                        'Argument "job" must have type '
                        'tmlib.tmaps.workflow.RunJob')
        super(RunJobCollection, self).add(job)


class CollectJob(Job):

    '''
    Class for TissueMAPS collect jobs, which can be processed once all
    parallel jobs are successfully completed.
    '''

    def __init__(self, step_name, arguments, output_dir):
        '''
        Initialize an instance of class CollectJob.

        Parameters
        ----------
        step_name: str
            name of the corresponding TissueMAPS workflow step
        arguments: List[str]
            command line arguments
        output_dir: str
            absolute path to the output directory, where log reports will
            be stored
        '''
        super(CollectJob, self).__init__(
            step_name=step_name,
            arguments=arguments,
            output_dir=output_dir)

    @property
    def name(self):
        '''
        Returns
        -------
        str
            name of the job
        '''
        return '%s_collect' % self.step_name


class WorkflowStep(SequentialTaskCollection):

    '''
    Class for a TissueMAPS workflow step, which is composed of a fixed
    collection of parallel run jobs and an optional collect job.
    Fixed means that the number of jobs and the arguments are known in advance. 
    '''

    def __init__(self, name, run_jobs, collect_job=None):
        '''
        Initialize an instance of class WorkflowStep.

        Parameters
        ----------
        name: str
            name of the step
        run_jobs: tmlib.tmaps.workflow.RunJobCollection
            collection of run jobs that should be processed in parallel
        collect_job: tmlib.tmaps.workflow.CollectJob, optional
            optional job to collect output of run jobs
            (default: ``None``)
        '''
        self.name = name
        self.run_jobs = run_jobs
        if not isinstance(run_jobs, RunJobCollection):
            raise TypeError(
                        'Argument "run_jobs" must have type '
                        'tmlib.tmaps.workflow.RunJobCollection')
        self.tasks = [self.run_jobs]
        self.collect_job = collect_job
        if self.collect_job is not None:
            if not isinstance(self.collect_job, CollectJob):
                raise TypeError(
                            'Argument "collect_job" must have type '
                            'tmlib.tmaps.workflow.CollectJob')
            self.tasks.append(self.collect_job)
        super(WorkflowStep, self).__init__(tasks=self.tasks, jobname=name)


class WorkflowStage(SequentialTaskCollection, StopOnError):

    '''
    Class for a TissueMAPS workflow stage, which is composed of one or more
    workflow steps. The number of jobs and the arguments are know for the first
    step of the stage, but not for the subsequent steps, since their input
    depends on the output of previous steps.
    Subsequent steps are thus build dynamically upon transition from one step
    to the other.
    '''

    def __init__(self, name, experiment, verbosity, description=None,
                 start_step=None):
        '''
        Initialize an instance of class WorkflowStage.

        Parameters
        ----------
        name: str
            name of the stage
        experiment: str
            configured experiment object
        verbosity: int
            logging verbosity level
        description: tmlib.tmaps.description.WorkflowStageDescription, optional
            description of the stage (default: ``None``)
        start_step: str or int, optional
            name or index of a step from where the stage should be started
            (default: ``None``)
        '''
        super(WorkflowStage, self).__init__(tasks=None, jobname='%s' % name)
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
        if description is None:
            raise ValueError(
                        'Description was not provided and could not be '
                        'determined from user configuration file.')
        self.start_step = start_step
        # self.expected_outputs = list()
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

    def _create_jobs_for_next_step(self, step):
        logger.debug('create jobs for step "%s"', step.name)
        prog_name = step.name
        logger.debug('load program "%s"', prog_name)
        prog = load_program(prog_name)
        logger.debug('create a program instance')
        prog_instance = prog(self.experiment, self.verbosity)

        logger.debug('call "init" method with configured arguments')
        prog_instance.init(step.args)
        # # Check whether inputs of current step were generated by previous steps
        # if not all([
        #             os.path.exists(i)
        #             for i in prog_instance.required_inputs
        #         ]):
        #     logger.error('required inputs were not generated')
        #     raise WorkflowTransitionError('required inputs do not exist')

        # # Store the expected outputs to be later able to check whether they
        # # were actually generated
        # self.expected_outputs.append(prog_instance.expected_outputs)

        logger.debug('build GC3Pie jobs')
        logger.info('allocated time for jobs: %s', step.duration)
        logger.info('allocated memory for jobs: %d GB', step.memory)
        logger.info('allocated cores for jobs: %d', step.cores)
        jobs = prog_instance.build_jobs(
                        duration=step.duration,
                        memory=step.memory,
                        cores=step.cores)
        return jobs

    def _add_step(self, index):
        # if index == 0:
        #     logger.info('create job descriptions for first step')
        # if index > 0:
        #     if not all([os.path.exists(f) for f in self.expected_outputs[-1]]):
        #         logger.error('expected outputs were not generated')
        #         raise WorkflowTransitionError(
        #                      'outputs of previous step do not exist')
        #     logger.debug('create job descriptions for next step')
        task = self._create_jobs_for_next_step(self._steps_to_process[index])
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
        if done+1 < len(self._steps_to_process):
            logger.info('step "%s" is done', self._steps_to_process[done].name)
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
                logger.debug('set exitcode to one')
                logger.debug('set state to TERMINATED')
                return Run.State.TERMINATED

        return super(WorkflowStage, self).next(done)


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
            logging verbosity level
        description: tmlib.tmaps.description.WorkflowDescription, optional
            description of the workflow (default: ``None``)
        start_stage: str or int, optional
            name or index of a stage from where the workflow should be
            started (default: ``None``)
        start_step: str or int, optional
            name or index of a step from where `start_stage` should be started
            (default: ``None``)
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
        task = WorkflowStage(
                    name=stage.name,
                    experiment=self.experiment,
                    verbosity=self.verbosity,
                    description=stage,
                    start_step=start_step)
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
        if done+1 < len(self._stages_to_process):
            logger.info('stage "%s" is done', self._stages_to_process[done].name)
            wait = 120
            logger.debug('wait %d seconds', wait)
            time.sleep(wait)
            try:
                stage_names = [s.name for s in self.description.stages]
                next_stage_name = self._stages_to_process[done+1].name
                next_stage_index = stage_names.index(next_stage_name)
                logger.info('transit to next stage ({0} of {1}): "{2}"'.format(
                            next_stage_index, self.n_stages, next_stage_name))
                self._add_stage(done+1)
            except Exception as error:
                logger.error('adding next stage failed: %s', error)
                self.execution.exitcode = 1
                logger.debug('set exitcode to one')
                logger.debug('set state to TERMINATED')
                return Run.State.TERMINATED

        return super(Workflow, self).next(done)
