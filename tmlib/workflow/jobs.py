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
import logging
from abc import ABCMeta
from abc import abstractproperty
# from gc3libs.workflow import RetryableTask
from gc3libs.workflow import (
    AbortOnError, SequentialTaskCollection, ParallelTaskCollection
)
from gc3libs.persistence.sql import IdFactory, IntId

from tmlib.jobs import Job

logger = logging.getLogger(__name__)

_idfactory = IdFactory(id_class=IntId)


class WorkflowStepJob(Job):

    '''Abstract base class for an individual job as part of a
    workflow step phase.

    Note
    ----
    Jobs are constructed based on descriptions, which persist on disk
    in form of *JSON* files.
    '''

    __metaclass__ = ABCMeta

    def __init__(self, step_name, arguments, output_dir,
                 submission_id, user_name, parent_id, **extra_args):
        '''
        Parameters
        ----------
        step_name: str
            name of the corresponding TissueMAPS workflow step
        arguments: List[str]
            command line arguments
        output_dir: str
            absolute path to the output directory, where log reports will
            be stored
        submission_id: int
            ID of the corresponding submission
        user_name: str
            name of the submitting user
        parent_id: int
            ID of the parent
            :class:`JobCollection <tmlib.workflow.jobs.JobCollection>`

        See also
        --------
        :class:`tmlib.models.submission.Submission`

        Note
        ----
        When submitting with `SLURM` backend, there must be an existing account
        for `user_name`.
        '''
        self.step_name = step_name
        super(WorkflowStepJob, self).__init__(
            arguments, output_dir, submission_id, user_name, parent_id,
            # pass extra arguments up to superclass ctor
            **extra_args
        )

    @abstractproperty
    def name(self):
        '''str:name of the job'''


class InitJob(WorkflowStepJob):

    '''Class for a *init* jobs, which creates the descriptions for the
    subsequent *run* and *collect* phases.
    '''

    def __init__(self, step_name, arguments, output_dir, submission_id,
                 user_name, parent_id, **extra_args):
        '''
        Parameters
        ----------
        step_name: str
            name of the corresponding TissueMAPS workflow step
        arguments: List[str]
            command line arguments
        output_dir: str
            absolute path to the output directory, where log reports will
            be stored
        submission_id: int
            ID of the corresponding submission
        user_name: str
            name of the submitting user
        parent_id: int
            ID of the parent :class:`InitPhase <tmlib.workflow.jobs.InitPhase>`
        **extra_args
            Any additional keyword arguments are passed unchanged
            to the parent class constructor
        '''
        super(self.__class__, self).__init__(
            step_name=step_name,
            arguments=arguments,
            output_dir=output_dir,
            submission_id=submission_id,
            user_name=user_name,
            parent_id=parent_id,
            # pass extra arguments up to superclass ctor
            **extra_args
        )

    @property
    def name(self):
        '''str:name of the job'''
        return '%s_init_%.7d' % (self.step_name, 1)


class RunJob(WorkflowStepJob):

    '''Class for TissueMAPS run jobs, which can be processed in parallel.'''

    def __init__(self, step_name, arguments, output_dir, job_id,
                 submission_id, user_name, parent_id, index=None,
                 **extra_args):
        '''
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
        submission_id: int
            ID of the corresponding submission
        parent_id: int
            ID of the parent :class:`RunPhase <tmlib.workflow.jobs.RunPhase>`
        index: int, optional
            index of the *run* job collection in case the step has multiple
            *run* phases
        **extra_args
            Any additional keyword arguments are passed unchanged
            to the parent class constructor
        '''
        self.job_id = job_id
        if not isinstance(index, int) and index is not None:
            raise TypeError('Argument "index" must have type int.')
        self.index = index
        super(RunJob, self).__init__(
            step_name=step_name,
            arguments=arguments,
            output_dir=output_dir,
            submission_id=submission_id,
            user_name=user_name,
            parent_id=parent_id,
            # pass extra arguments up to superclass ctor
            **extra_args
        )

    @property
    def name(self):
        '''str: name of the job'''
        if self.index is None:
            return '%s_run_%.7d' % (self.step_name, self.job_id)
        else:
            return (
                '%s_run-%.2d_%.7d' % (self.step_name, self.index, self.job_id)
            )


class CollectJob(WorkflowStepJob):

    '''Class for a collect jobs, which can be processed once all
    parallel jobs are successfully completed.
    '''

    def __init__(self, step_name, arguments, output_dir, submission_id,
                 user_name, parent_id, **extra_args):
        '''
        Parameters
        ----------
        step_name: str
            name of the corresponding TissueMAPS workflow step
        arguments: List[str]
            command line arguments
        output_dir: str
            absolute path to the output directory, where log reports will
            be stored
        submission_id: int
            ID of the corresponding submission
        user_name: str
            name of the submitting user
        parent_id: int
            ID of the parent
            :class:`CollectPhase <tmlib.workflow.jobs.CollectPhase>`
        **extra_args
            Any additional keyword arguments are passed unchanged
            to the parent class constructor
        '''
        super(self.__class__, self).__init__(
            step_name=step_name,
            arguments=arguments,
            output_dir=output_dir,
            submission_id=submission_id,
            user_name=user_name,
            parent_id=parent_id,
            # pass extra arguments up to superclass ctor
            **extra_args
        )

    @property
    def name(self):
        '''str:name of the job'''
        return '%s_collect_%.7d' % (self.step_name, 1)


class JobCollection(object):

    '''Abstract base class for collections of individual jobs.'''

    __metaclass__ = ABCMeta


class InitPhase(ParallelTaskCollection, JobCollection):

    '''Collection of jobs for the "init" phase of a workflow step.'''

    def __init__(self, step_name, submission_id, parent_id, job=None):
        '''
        Parameters
        ----------
        step_name: str
            name of the parent
            :class:`WorkflowStep <tmlib.workflow.workflow.WorkflowStep>`
        submission_id: int
            ID of the corresponding
            :class:`Submission <tmlib.models.submission.Submission>`
        parent_id: int
            ID of the parent
            :class:`WorkflowStep <tmlib.workflow.workflow.WorkflowStep>`
        job: tmlibs.workflow.jobs.InitJob, optional
            job that should be processed (default: ``None``)
        '''
        self.step_name = step_name
        tasks = []
        if job is not None:
            if not isinstance(job, InitJob):
                raise TypeError(
                    'Argument "job" must have type tmlib.workflow.jobs.InitJob'
                )
            tasks.append(job)
        self.name = '%s_init' % self.step_name
        self.parent_id = parent_id
        self.persistent_id = _idfactory.new(self)
        self.submission_id = submission_id
        super(self.__class__, self).__init__(jobname=self.name, tasks=tasks)

    def add(self, job):
        '''Adds a job to the phase.

        Parameters
        ----------
        job: tmlibs.workflow.jobs.InitJob
            job that should be added

        Raises
        ------
        TypeError
            when `job` has wrong type
        ValueError
            when the phase already contains another job
        '''
        if not isinstance(job, InitJob):
            raise TypeError(
                'Argument "job" must have type '
                'tmlib.workflow.jobs.InitJob'
            )
        if len(self.tasks) > 0:
            raise ValueError('InitPhase can only contain a single job.')
        super(self.__class__, self).add(job)

    def __repr__(self):
        return (
            '<%s(name=%r, submission_id=%r)>'
            % (self.__class__.__name__, self.name, self.submission_id)
        )


class CollectPhase(ParallelTaskCollection, JobCollection):

    '''Collection of jobs for the "collect" phase of a workflow step.'''

    def __init__(self, step_name, submission_id, parent_id, job=None):
        '''
        Parameters
        ----------
        step_name: str
            name of the corresponding
            :class:`WorkflowStep <tmlib.workflow.workflow.WorkflowStep>`
        submission_id: int
            ID of the corresponding
            :class:`Submission <tmlib.models.submission.Submission>`
        parent_id: int
            ID of the parent
            :class:`WorkflowStep <tmlib.workflow.workflow.WorkflowStep>`
        job: tmlibs.workflow.jobs.CollectJob, optional
            job that should be processed (default: ``None``)
        '''
        self.step_name = step_name
        tasks = []
        if job is not None:
            if not isinstance(job, CollectJob):
                raise TypeError(
                    'Argument "job" must have type '
                    'tmlib.workflow.jobs.CollectJob'
                )
            tasks.append(job)
        self.name = '%s_collect' % self.step_name
        self.parent_id = parent_id
        self.persistent_id = _idfactory.new(self)
        self.submission_id = submission_id
        super(self.__class__, self).__init__(jobname=self.name, tasks=tasks)

    def add(self, job):
        '''Adds a job to the phase.

        Parameters
        ----------
        job: tmlibs.workflow.jobs.CollectJob
            job that should be added

        Raises
        ------
        TypeError
            when `job` has wrong type
        ValueError
            when the phase already contains another job
        '''
        if not isinstance(job, CollectJob):
            raise TypeError(
                'Argument "job" must have type '
                'tmlib.workflow.jobs.CollectJob'
            )
        if len(self.tasks) > 0:
            raise ValueError('CollectPhase can only contain a single job.')
        super(self.__class__, self).add(job)

    def __repr__(self):
        return (
            '<%s(name=%r, submission_id=%r)>'
            % (self.__class__.__name__, self.name, self.submission_id)
        )


class RunPhase(JobCollection):

    '''Abstract base class for a collection of jobs for the "run" phase of a
    workflow step.
    '''

    __metaclass__ = ABCMeta


class SingleRunPhase(ParallelTaskCollection, RunPhase):

    '''Collection of jobs for the "run" phase of workflow step that consits
    of a single job collection.
    '''

    def __init__(self, step_name, submission_id, parent_id, jobs=None,
            index=None):
        '''
        Parameters
        ----------
        step_name: str
            name of the corresponding
            :class:`WorkflowStep <tmlib.workflow.workflow.WorkflowStep>`
        submission_id: int
            ID of the corresponding
            :class:`Submission <tmlib.models.submission.Submission>`
        parent_id: int
            ID of the parent
            :class:`WorkflowStep <tmlib.workflow.workflow.WorkflowStep>`
        jobs: List[tmlibs.workflow.jobs.RunJob], optional
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
                    'tmlib.workflow.jobs.RunJob'
                )
        if index is None:
            self.name = '%s_run' % self.step_name
        else:
            if not isinstance(index, int):
                raise TypeError('Argument "index" must have type int.')
            self.name = '%s_run-%.2d' % (self.step_name, index)
        self.parent_id = parent_id
        self.persistent_id = _idfactory.new(self)
        self.submission_id = submission_id
        super(self.__class__, self).__init__(jobname=self.name, tasks=jobs)

    def add(self, job):
        '''Adds a job to the phase.

        Parameters
        ----------
        job: tmlibs.workflow.jobs.RunJob
            job that should be added

        Raises
        ------
        TypeError
            when `job` has wrong type
        '''
        if not isinstance(job, RunJob):
            raise TypeError(
                'Argument "job" must have type '
                'tmlib.workflow.jobs.RunJob'
            )
        super(self.__class__, self).add(job)

    def __repr__(self):
        return (
            '<%s(name=%r, n=%r, submission_id=%r)>'
            % (self.__class__.__name__, self.name, len(self.tasks),
                self.submission_id)
        )


class MultiRunPhase(AbortOnError, SequentialTaskCollection, RunPhase):

    '''Collection of jobs for the "run" phase of workflow step that consits
    of multiple nested job collections that should be processed sequentially.
    '''

    def __init__(self, step_name, submission_id, parent_id,
            run_job_collections=list()):
        '''
        Parameters
        ----------
        step_name: str
            name of the corresponding
            :class:`WorkflowStep <tmlib.workflow.workflow.WorkflowStep>`
        submission_id: int
            ID of the corresponding
            :class:`Submission <tmlib.models.submission.Submission>`
        parent_id: int
            ID of the parent
            :class:`WorkflowStep <tmlib.workflow.workflow.WorkflowStep>`
        run_job_collections: List[tmlib.workflow.jobs.SingleRunPhase], optional
            collections of run jobs that should be processed one after another
        '''
        self.name = '%s_run' % step_name
        self.step_name = step_name
        self.parent_id = parent_id
        self.persistent_id = _idfactory.new(self)
        self.submission_id = submission_id
        if run_job_collections is None:
            run_job_collections = list()
        super(self.__class__, self).__init__(
            jobname=self.name, tasks=run_job_collections
        )

    def add(self, run_job_collection):
        '''Add a collection of run jobs to the phase.

        Parameters
        ----------
        run_job_collection: tmlib.workflow.jobs.SingleRunPhase
            collection of run jobs that should be added

        Raises
        ------
        TypeError
            when `run_job_collection` has wrong type
        '''
        if not isinstance(run_job_collection, SingleRunPhase):
            raise TypeError(
                'Argument "run_job_collection" must have type '
                'tmlib.workflow.jobs.SingleRunPhase'
            )
        super(self.__class__, self).add(run_job_collection)

    def __repr__(self):
        return (
            '<%s(name=%r, n=%r, submission_id=%r)>'
            % (self.__class__.__name__, self.name, len(self.tasks),
                self.submission_id)
        )


class IndependentJobCollection(SequentialTaskCollection, JobCollection):

    '''Collection of jobs for manual submission of the *run* and *collect*
    phases of a workflow steps independent of the main workflow.
    '''

    def __init__(self, step_name, submission_id, jobs=None):
        '''
        Parameters
        ----------
        step_name: str
            name of the corresponding TissueMAPS workflow step
        submission_id: int
            ID of the corresponding submission
        jobs: List[tmlibs.workflow.jobs.RunPhase or tmlibs.workflow.jobs.CollectJob], optional
            list of jobs that should be processed (default: ``None``)
        '''
        self.submission_id = submission_id
        if jobs is not None:
            if not isinstance(jobs[0], RunPhase):
                raise TypeError(
                    'First job must have type '
                    'tmlib.workflow.jobs.RunPhase.'
                )
        self.persistent_id = _idfactory.new(self)
        super(self.__class__, self).__init__(jobname=step_name, tasks=jobs)
