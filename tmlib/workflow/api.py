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
import re
import os
import yaml
import glob
import time
import logging
import numpy as np
import datetime
import inspect
import sqlalchemy.orm
from natsort import natsorted
from abc import ABCMeta
from abc import abstractmethod
from abc import abstractproperty
import gc3libs
from gc3libs.quantity import Duration, Memory

import tmlib.models as tm
from tmlib import cfg
from tmlib import utils
from tmlib.readers import JsonReader
from tmlib.writers import JsonWriter
from tmlib.workflow import get_step_args
from tmlib.workflow import WorkflowStep
from tmlib.errors import (
    WorkflowError, WorkflowDescriptionError, WorkflowTransitionError,
    JobDescriptionError, CliArgError
)
from tmlib.workflow.jobs import (
    InitJob, RunJob, CollectJob,
    SingleRunPhase, InitPhase, RunPhase, CollectPhase
)

logger = logging.getLogger(__name__)


def _is_sqla_mapper_class(obj):
    try:
        class_mapper(obj)
        return True
    except:
        return False


def _is_model_class(obj):
    return (
        _inspect.isclass(obj) and
        _is_sqla_mapper_class(obj) and
        tm.ExperimentModel in inspect.getmro(self.generated_outputs)
    )


def _is_model_class_attr(obj):
    return (
        _is_model_class(obj.__class__) and
        isinstance(obj, sqlalchemy.orm.attributes.InstrumentedAttribute)
    )


class BasicWorkflowStepAPI(object):

    '''Abstract base class for cluster routines.'''

    __metaclass__ = ABCMeta

    @property
    def datetimestamp(self):
        '''
        Returns
        -------
        str
            datetime stamp in the form "year-month-day_hour:minute:second"
        '''
        return utils.create_datetimestamp()

    @property
    def timestamp(self):
        '''
        Returns
        -------
        str
            time stamp in the form "hour:minute:second"
        '''
        return utils.create_timestamp()


class _ApiMeta(ABCMeta):

    '''Metaclass for
    :class:`WorkflowStepAPI <tmlib.workflow.api.WorkflowStepAPI>`.

    The metaclass inspects the method *collect_job_output* of derived classes
    to dynamically determine whether the given step has implemented the
    *collect* phase.
    '''

    def __init__(cls, clsname, bases, attrs):
        super(_ApiMeta, cls).__init__(clsname, bases, attrs)
        if '__abstract__' in vars(cls).keys():
            return
        collect_method = getattr(cls, 'collect_job_output')
        if getattr(collect_method, 'is_implemented', True):
            has_collect_phase = True
        else:
            has_collect_phase = False
        # NOTE: This attribute will be used by the constructor of the
        # WorkflowStep class to determine whether a "collect" job has to be
        # created for that step.
        setattr(cls, 'has_collect_phase', has_collect_phase)


class WorkflowStepAPI(BasicWorkflowStepAPI):

    '''Abstract base class for API classes, which provide methods for
    for large-scale image processing on a batch cluster.

    Each workflow step must implement this class and decorate it with
    :func:`register_step_api <tmlib.workflow.register_step_api>` to register
    it for use within a :class:`Workflow <tmlib.workflow.workflow.Workflow>`.

    Note
    ----
    Classes that don't implement the *collect* phase must decorate the
    implemented ``collect_job_output()`` method with
    :func:`notimplemented <tmlib.utils.notimplemented>`.
    '''

    __metaclass__ = _ApiMeta

    __abstract__ = True

    def __init__(self, experiment_id):
        '''
        Parameters
        ----------
        experiment_id: int
            ID of the processed experiment

        Attributes
        ----------
        experiment_id: int
            ID of the processed experiment
        workflow_location: str
            absolute path to location where workflow related data should be
            stored
        '''
        super(WorkflowStepAPI, self).__init__()
        self.experiment_id = experiment_id
        with tm.utils.ExperimentSession(experiment_id) as session:
            experiment = session.query(tm.Experiment).get(self.experiment_id)
            if experiment is None:
                raise CliArgError(
                    'No experiment with ID %d found.' % self.experiment_id
                )
            self.workflow_location = experiment.workflow_location

    @property
    def step_name(self):
        '''str: name of the step'''
        return self.__module__.split('.')[-2]

    @staticmethod
    def _create_batches(li, n):
        return utils.create_partitions(li, n)

    @utils.autocreate_directory_property
    def step_location(self):
        '''str: location were step-specific data is stored'''
        return os.path.join(self.workflow_location, self.step_name)

    @utils.autocreate_directory_property
    def log_location(self):
        '''str: location where log files are stored'''
        return os.path.join(self.step_location, 'log')

    @utils.autocreate_directory_property
    def batches_location(self):
        '''str: location where job description files are stored'''
        return os.path.join(self.step_location, 'batches')

    def get_run_job_ids(self):
        '''Gets IDs of jobs of the *run* phase from persisted descriptions.

        Returns
        -------
        List[int]
            job IDs

        '''
        job_description_files = glob.glob(
            os.path.join(self.batches_location, '*_run_*.batch.json')
        )
        if not job_description_files:
            raise IOError('No batches found.')
        job_ids = list()
        for f in job_description_files:
            j = int(re.search(r'_run_(\d+)\.batch.json', f).groups()[0])
            job_ids.append(j)

        return job_ids

    def get_log_output(self, phase, job_id=None):
        '''Gets log outputs (standard output and error).

        Parameters
        ----------
        phase: str
            phase of the workflow step (options: ``{"init", "run", "collect"}``)
        job_id: int, optional
            one-based identifier number of "run" jobs (default: ``None``)

        Returns
        -------
        Dict[str, str]
            "stdout" and "stderr" for the given job

        Note
        ----
        In case there are several log files present for the given the most
        recent one will be used (sorted by submission date and time point).
        '''
        if phase == 'run':
            if not isinstance(job_id, int):
                raise ValueError(
                    'Argument "job_id" is required for "run" phase.'
                )
            stdout_files = glob.glob(
                os.path.join(self.log_location, '*_run*_%.7d*.out' % job_id)
            )
            stderr_files = glob.glob(
                os.path.join(self.log_location, '*_run*_%.7d*.err' % job_id)
            )
            if not stdout_files or not stderr_files:
                raise IOError('No log files found for run job # %d' % job_id)
        else:
            stdout_files = glob.glob(
                os.path.join(self.log_location, '*_%s_*.out' % phase)
            )
            stderr_files = glob.glob(
                os.path.join(self.log_location, '*_%s_*.err' % phase)
            )
            if not stdout_files or not stderr_files:
                raise IOError('No log files found for "%s" job' % phase)
        # Take the most recent log files
        log = dict()
        with open(natsorted(stdout_files)[-1], 'r') as f:
            log['stdout'] = f.read()
        with open(natsorted(stderr_files)[-1], 'r') as f:
            log['stderr'] = f.read()
        return log

    def _build_batch_filename_for_run_job(self, job_id):
        return os.path.join(
            self.batches_location,
            '%s_run_%.7d.batch.json' % (self.step_name, job_id)
        )

    def _build_batch_filename_for_collect_job(self):
        return os.path.join(
            self.batches_location,
            '%s_collect.batch.json' % self.step_name
        )

    def get_run_batch(self, job_id):
        '''Get description for a :class:`RunJob <tmlib.workflow.jobs.RunJob>`.

        Parameters
        ----------
        job_id: int
            one-based job identifier

        Returns
        -------
        Dict[str, Union[int, str, list, dict]]
            job description
        '''
        logger.debug('get batch for run job #%d', job_id)
        batch_filename = self._build_batch_filename_for_run_job(job_id)
        return self._read_batch_file(batch_filename)

    def get_collect_batch(self):
        '''Get description for a
        :class:`CollectJob <tmlib.workflow.jobs.CollectJob>`.

        Returns
        -------
        Dict[str, Union[int, str, list, dict]]
            job description
        '''
        logger.debug('get batch for collect job')
        batch_filename = self._build_batch_filename_for_collect_job()
        return self._read_batch_file(batch_filename)

    def store_run_batch(self, batch, job_id):
        '''Persists description for a
        :class:`RunJob <tmlib.workflow.jobs.RunJob>`.

        Parameters
        ----------
        batch: Dict[str, Union[int, str, list, dict]]
            JSON serializable job description
        job_id: str
            job ID
        '''
        logger.debug('store batch for run job #%d', job_id)
        filename = self._build_batch_filename_for_run_job(job_id)
        self._write_batch_file(filename, batch)

    def store_collect_batch(self, batch):
        '''Persists description for a
        :class:`CollectJob <tmlib.workflow.jobs.CollectJob>`.

        Parameters
        ----------
        batch: Dict[str, Union[int, str, list, dict]]
            JSON serializable job description
        '''
        logger.debug('store batch for collect job')
        filename = self._build_batch_filename_for_collect_job()
        self._write_batch_file(filename, batch)

    def _read_batch_file(self, filename):
        if not os.path.exists(filename):
            raise OSError(
                'Job description file does not exist: %s.\n'
                'Initialize the step first by calling the "init" method.'
                % filename
            )
        with JsonReader(filename) as f:
            batch = f.read()
        return batch

    def _write_batch_file(self, filename, batch):
        with JsonWriter(filename) as f:
            f.write(batch)

    def _build_init_command(self, batch_args, verbosity):
        logger.debug('build "init" command')
        command = [self.step_name]
        command.extend(['-v' for x in range(verbosity)])
        command.append(self.experiment_id)
        command.append('init')
        for arg in batch_args.iterargs():
            value = getattr(batch_args, arg.name)
            if arg.type == bool:
                if ((value and not arg.default) or
                    (not value and arg.default)):
                    command.append('--%s' % arg.flag)
            else:
                if value is not None:
                    command.extend(['--%s' % arg.flag, str(value)])
        return command

    def _build_run_command(self, job_id, verbosity):
        logger.debug('build "run" command')
        command = [self.step_name]
        command.extend(['-v' for x in range(verbosity)])
        command.append(self.experiment_id)
        command.extend(['run', '--job', str(job_id), '--assume-clean-state'])
        return command

    def _build_collect_command(self, verbosity):
        logger.debug('build "collect" command')
        command = [self.step_name]
        command.extend(['-v' for x in range(verbosity)])
        command.append(self.experiment_id)
        command.extend(['collect'])
        return command

    @abstractmethod
    def run_job(self, batch, assume_clean_state=False):
        '''Runs an individual job.

        Parameters
        ----------
        batch: dict
            description of the job
        assume_clean_state: bool, optional
            assume that output of previous runs has already been cleaned up

        Note
        ----
        Each job should be atomic. This implies that it should remove any output
        of a previous run when necessary to ensure data consistency, e.g.
        prevent dublication of data. This can be relaxed when the job is run as
        part of a :class:`WorkflowStep <tmlib.workflow.workflow.WorkflowStep>`,
        because the *init* phase will clean-up any existing output of previous
        runs. Setting `assume_clean_state` would thus be appropriate in this
        context. It is up to the developer to implement this logic in a step
        accordingly.
        '''
        pass

    @abstractmethod
    def delete_previous_job_output(self):
        '''Deletes the output of a previous submission.'''
        pass

    @abstractmethod
    def collect_job_output(self, batch):
        '''Collects the output of jobs and fuse them if necessary.

        Parameters
        ----------
        batches: List[dict]
            job descriptions
        **kwargs: dict
            additional variable input arguments as key-value pairs
        '''
        pass

    @abstractmethod
    def create_run_batches(self, args):
        '''Creates job descriptions with information required for
        processing of individual batch jobs of the parallel *run* phase.

        Each batch is a mapping that must provide at least the following
        key-value pair:

            * "id": one-based job identifier number (*int*)

        Additional key-value pairs may be provided, depending on requirements
        of the step.

        Parameters
        ----------
        args: tmlib.workflow.args.BatchArguments
            an instance of a step-specific implementation
            :class:`BatchArguments <tmlib.workflow.args.BatchArguments>`

        Returns
        -------
        Union[List[dict], generator]]
            job descriptions
        '''
        pass

    def create_collect_batch(self, args):
        '''Creates a job description with information required for
        processing of the batch job of the optional *collect* phase.

        This method returns an empty dictionary. In case the step implements
        the *collect* phase and arguments need to be parsed to
        :meth:`collect_job_output <tmlib.workflow.api.WorkflowStepAPI.collect_job_output>`,
        the derived class can override this method.

        Parameters
        ----------
        args: tmlib.workflow.args.BatchArguments
            an instance of a step-specific implementation
            :class:`BatchArguments <tmlib.workflow.args.BatchArguments>`

        Returns
        -------
        dict
            job description
        '''
        return {}

    def print_job_descriptions(self, batches):
        '''Prints job descriptions to standard output in YAML format.

        Parameters
        ----------
        batches: Dict[List[dict]]
            description of inputs and outputs or individual jobs
        '''
        print yaml.safe_dump(batches, default_flow_style=False)

    def create_step(self, submission_id, user_name, description):
        '''Creates the workflow step.

        Parameters
        ----------
        submission_id: int
            ID of the corresponding submission
        user_name: str
            name of the submitting user
        description: tmlib.workflow.description.WorkflowStepDescription

        Returns
        -------
        tmlib.workflow.WorkflowStep
        '''
        logger.debug('create workflow step for submission %d', submission_id)
        return WorkflowStep(
            name=self.step_name,
            submission_id=submission_id,
            user_name=user_name,
            description=description
        )

    def create_init_phase(self, submission_id, parent_id):
        '''Creates a job collection for the "init" phase of the step.

        Parameters
        ----------
        submission_id: int
            ID of the corresponding
            :class:`Submission <tmlib.models.submission.Submission>`
        parent_id: int
            ID of the parent
            :class:`WorkflowStep <tmlib.workflow.workflow.WorkflowStep>`

        Returns
        -------
        tmlib.workflow.job.InitPhase
            collection of "init" jobs
        '''
        return InitPhase(
            step_name=self.step_name, submission_id=submission_id,
            parent_id=parent_id
        )

    def create_run_phase(self, submission_id, parent_id):
        '''Creates a job collection for the "run" phase of the step.

        Parameters
        ----------
        submission_id: int
            ID of the corresponding
            :class:`Submission <tmlib.models.submission.Submission>`
        parent_id: int
            ID of the parent
            :class:`WorkflowStep <tmlib.workflow.workflow.WorkflowStep>`

        Returns
        -------
        tmlib.workflow.job.SingleRunPhase
            collection of "run" jobs
        '''
        return SingleRunPhase(
            step_name=self.step_name, submission_id=submission_id,
            parent_id=parent_id
        )

    def create_collect_phase(self, submission_id, parent_id):
        '''Creates a job collection for the "collect" phase of the step.

        Parameters
        ----------
        submission_id: int
            ID of the corresponding
            :class:`Submission <tmlib.models.submission.Submission>`
        parent_id: int
            ID of the parent
            :class:`WorkflowStep <tmlib.workflow.workflow.WorkflowStep>`

        Returns
        -------
        tmlib.workflow.job.CollectPhase
            collection of "collect" jobs
        '''
        return CollectPhase(
            step_name=self.step_name, submission_id=submission_id,
            parent_id=parent_id
        )

    def create_run_jobs(self, user_name, job_collection,
            verbosity, duration, memory, cores):
        '''Creates jobs for the parallel "run" phase of the step.

        Parameters
        ----------
        user_name: str
            name of the submitting user
        job_collection: tmlib.workflow.job.RunPhase
            empty collection of *run* jobs that should be populated
        verbosity: int
            logging verbosity for jobs
        duration: str
            computational time that should be allocated for a single job;
            in HH:MM:SS format
        memory: int
            amount of memory in Megabyte that should be allocated for a single
            job
        cores: int
            number of CPU cores that should be allocated for a single job

        Returns
        -------
        tmlib.workflow.jobs.RunPhase
            collection of jobs
        '''
        logger.info(
            'create "run" jobs for submission %d', job_collection.submission_id
        )

        if cores > cfg.resource.max_cores_per_job:
            logger.warn(
                'requested cores exceed available cores per node:  %s',
                cfg.resource.max_cores_per_job
            )
            logger.debug(
                'setting number of cores to %d', cfg.resource.max_cores_per_job
            )
            cores = cfg.resource.max_cores_per_job

        max_memory_per_node = (
            cfg.resource.max_cores_per_job *
            cfg.resource.max_memory_per_core.amount(Memory.MB)
        )
        max_memory_per_core = cfg.resource.max_memory_per_core.amount(Memory.MB)
        if cores == 1:
            if memory > max_memory_per_core:
                logger.warn(
                    'requested memory exceeds available memory per core: %d MB',
                    max_memory_per_core
                )
                memory = max_memory_per_core
        else:
            if memory > max_memory_per_node:
                logger.warn(
                    'requested memory exceeds available memory per node: %d MB',
                    max_memory_per_node
                )
                logger.debug('setting memory to %d MB', max_memory_per_node)
                memory = max_memory_per_node

        logger.debug('allocated time for run jobs: %s', duration)
        logger.debug('allocated memory for run jobs: %d MB', memory)
        logger.debug('allocated cores for run jobs: %d', cores)

        job_ids = self.get_run_job_ids()
        for j in job_ids:
            job_collection.add(
                RunJob(
                    **self._get_run_job_args(
                        step_name=self.step_name,
                        arguments=self._build_run_command(j, verbosity),
                        output_dir=self.log_location,
                        job_id=j,
                        submission_id=job_collection.submission_id,
                        user_name=user_name,
                        parent_id=job_collection.persistent_id,
                        requested_walltime = Duration(duration),
                        requested_memory = Memory(memory, Memory.MB),
                        requested_cores = cores,
                    )
                )
            )
        return job_collection

    # FIXME: the existence of this method proves that we're trying to
    # re-implement class inheritance which was basically thrown out by
    # having all these `create_*_jobs` methods conflated in a single
    # class.  We should instead restructure code to use one class for
    # each kind of Job/Task and use constructors and normal class
    # inheritance to create objects, not generic factory methods!
    def _get_run_job_args(self, **args):
        '''
        Build dictionary of arguments for constructing a "RunJob" instance.

        Default implementation just passes input dict unchanged,
        must be overridden in sub-classes.
        '''
        return args

    def create_init_job(self, user_name, job_collection,
            batch_args, verbosity, duration='12:00:00'):
        '''Creates job for the "init" phase of the step.

        Parameters
        ----------
        user_name: str
            name of the submitting user
        job_collection: tmlib.workflow.job.InitPhase
            empty collection of *init* jobs that should be populated
        batch_args: tmlib.workflow.args.BatchArguments
            step-specific implementation of
            :class:`BatchArguments <tmlib.workflow.args.BatchArguments>`
        duration: str, optional
            computational time that should be allocated for the job
            in HH:MM:SS format (default: ``"12:00:00"``)
        verbosity: int
            logging verbosity for job

        Returns
        -------
        tmlib.workflow.jobs.InitPhase
            init job

        '''
        logger.info(
            'create "init" job for submission %d', job_collection.submission_id
        )
        memory = cfg.resource.max_memory_per_core
        cores = 1
        logger.debug('allocated time for "init" job: %s', duration)
        logger.debug('allocated memory for "init" job: %d MB', memory)
        logger.debug('allocated cores for "init" job: %d', cores)
        job = InitJob(
            step_name=self.step_name,
            arguments=self._build_init_command(batch_args, verbosity),
            output_dir=self.log_location,
            submission_id=job_collection.submission_id,
            user_name=user_name,
            parent_id=job_collection.persistent_id
        )
        job.requested_walltime = Duration(duration)
        job.requested_memory = Memory(memory, Memory.MB)
        job.requested_cores = cores
        job_collection.add(job)
        return job_collection

    def create_collect_job(self, user_name, job_collection,
            verbosity, duration='06:00:00'):
        '''Creates job for the "collect" phase of the step.

        Parameters
        ----------
        user_name: str
            name of the submitting user
        job_collection: tmlib.workflow.job.CollectPhase
            empty collection of *collect* jobs that should be populated
        verbosity: int
            logging verbosity for jobs
        duration: str, optional
            computational time that should be allocated for a single job;
            in HH:MM:SS format (default: ``"06:00:00"``)

        Returns
        -------
        tmlib.workflow.jobs.CollectJob
            collect job

        '''
        logger.info(
            'create "collect" job for submission %d', job_collection.submission_id
        )
        memory = cfg.resource.max_memory_per_core
        cores = 1
        logger.debug('allocated time for "collect" job: %s', duration)
        logger.debug('allocated memory for "collect" job: %d MB', memory)
        logger.debug('allocated cores for "collect" job: %d', cores)
        job = CollectJob(
            step_name=self.step_name,
            arguments=self._build_collect_command(verbosity),
            output_dir=self.log_location,
            submission_id=job_collection.submission_id,
            user_name=user_name,
            parent_id=job_collection.persistent_id
        )
        job.requested_walltime = Duration(duration)
        job.requested_memory = Memory(memory, Memory.MB)
        job.requested_cores = cores
        job_collection.add(job)
        return job_collection
