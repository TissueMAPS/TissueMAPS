import logging
from gc3libs.workflow import AbortOnError
from abc import ABCMeta
from abc import abstractproperty
import gc3libs
# from abc import abstractmethod
# from gc3libs.workflow import RetryableTask
from gc3libs.workflow import SequentialTaskCollection
from gc3libs.workflow import ParallelTaskCollection

from ..utils import create_datetimestamp

logger = logging.getLogger(__name__)


class Job(gc3libs.Application):

    '''
    Abstract base class for a `TissueMAPS` job.

    Note
    ----
    Jobs are constructed based on job descriptions, which persist on disk
    in form of JSON files.
    '''

    # TODO: inherit from RetryableTask(max_retries=1) and implement
    # re-submission logic by overwriting retry() method:
    # 
    #     with open(err_file, 'r') as err:
    #         if re.search(r'^FAILED', err, re.MULTILINE):
    #             reason = 'Exception'
    #         elif re.search(r'^TIMEOUT', err, re.MULTILINE):
    #             reason = 'Timeout'
    #         elif re.search(r'^[0-9]*\s*\bKilled\b', err, re.MULTILINE):
    #             reason = 'Memory'
    #         else:
    #             reason = 'Unknown'

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

    @property
    def is_terminated(self):
        '''
        Returns
        -------
        bool
            whether the job is in state TERMINATED
        '''
        return self.execution.state == gc3libs.Run.State.TERMINATED

    @property
    def is_running(self):
        '''
        Returns
        -------
        bool
            whether the job is in state RUNNING
        '''
        return self.execution.state == gc3libs.Run.State.RUNNING

    @property
    def is_stopped(self):
        '''
        Returns
        -------
        bool
            whether the job is in state STOPPED
        '''
        return self.execution.state == gc3libs.Run.State.STOPPED

    @property
    def is_submitted(self):
        '''
        Returns
        -------
        bool
            whether the job is in state SUBMITTED
        '''
        return self.execution.state == gc3libs.Run.State.SUBMITTED

    @property
    def is_new(self):
        '''
        Returns
        -------
        bool
            whether the job is state NEW
        '''
        return self.execution.state == gc3libs.Run.State.NEW


class RunJob(Job):

    '''
    Class for TissueMAPS run jobs, which can be processed in parallel.
    '''

    def __init__(self, step_name, arguments, output_dir, job_id, index=None):
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
        index: int, optional
            index of the *run* job collection in case the step has multiple
            *run* phases
        '''
        self.job_id = job_id
        if not isinstance(index, int) and index is not None:
            raise TypeError('Argument "index" must have type int.')
        self.index = index
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
        if self.index is None:
            return '%s_run_%.6d' % (self.step_name, self.job_id)
        else:
            return '%s_run-%.2d_%.6d' % (self.step_name, self.index, self.job_id)


class RunJobCollection(ParallelTaskCollection):

    '''
    Class for TissueMAPS run jobs based on a
    `gc3libs.workflow.ParallelTaskCollection`.
    '''

    def __init__(self, step_name, jobs=None, index=None):
        '''
        Initialize an instance of class RunJobCollection.

        Parameters
        ----------
        step_name: str
            name of the corresponding TissueMAPS workflow step
        jobs: List[tmlibs.tmaps.workflow.RunJob], optional
            list of jobs that should be processed (default: ``None``)
        index: int, optional
            index of the *run* job collection in case the step has multiple
            *run* phases
        '''
        self.step_name = step_name
        if jobs is not None:
            if not isinstance(jobs, list):
                raise TypeError('Argument "jobs" must have type list.')
            if not all([isinstance(j, RunJob) for j in jobs]):
                raise TypeError(
                        'Elements of argument "jobs" must have type '
                        'tmlib.jobs.RunJob')
        if index is None:
            name = '%s_run' % self.step_name
        else:
            if not isinstance(index, int):
                raise TypeError('Argument "index" must have type int.')
            name = '%s_run-%.2d' % (self.step_name, index)
        super(RunJobCollection, self).__init__(jobname=name, tasks=jobs)

    def add(self, job):
        '''
        Add a job.

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
                        'tmlib.jobs.RunJob')
        super(RunJobCollection, self).add(job)


class MultiRunJobCollection(AbortOnError, SequentialTaskCollection):

    def __init__(self, step_name, run_job_collections=None):
        '''
        Initialize an instance of class WorkflowStep.

        Parameters
        ----------
        step_name: str
            name of the corresponding TissueMAPS workflow step
        run_job_collections: List[tmlib.jobs.RunJobCollection], optional
            collections of run jobs that should be processed one after another
        '''
        self.step_name = step_name
        super(MultiRunJobCollection, self).__init__(
                    tasks=run_job_collections,
                    jobname='%s_multirun' % step_name)

    def add(self, run_job_collection):
        '''
        Add a collection of run jobs.

        Parameters
        ----------
        run_job_collection: exittmlib.jobs.RunJobCollection
            collection of run jobs that should be added

        Raises
        ------
        TypeError
            when `run_job_collection` has wrong type
        '''
        if not isinstance(run_job_collection, RunJobCollection):
            raise TypeError(
                        'Argument "run_job_collection" must have type '
                        'tmlib.jobs.RunJobCollection')
        super(MultiRunJobCollection, self).add(run_job_collection)


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
