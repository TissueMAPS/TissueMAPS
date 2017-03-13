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
    InitJob, RunJob, CollectJob, SingleRunJobCollection
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


class BasicClusterRoutines(object):

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

    '''Metaclass for :class:`tmlib.workflow.api.ClusterRoutines`.

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


class ClusterRoutines(BasicClusterRoutines):

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

    def __init__(self, experiment_id, verbosity):
        '''
        Parameters
        ----------
        experiment_id: int
            ID of the processed experiment
        verbosity: int
            logging level

        Attributes
        ----------
        experiment_id: int
            ID of the processed experiment
        verbosity: int
            logging level
        workflow_location: str
            absolute path to location where workflow related data should be
            stored
        '''
        super(ClusterRoutines, self).__init__()
        self.experiment_id = experiment_id
        self.verbosity = verbosity
        with tm.utils.MainSession() as session:
            experiment = session.query(tm.ExperimentReference).\
                get(self.experiment_id)
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

    def get_batches_from_files(self):
        '''Gets batches from files.

        Returns
        -------
        dict
            job descriptions

        Raises
        ------
        :exc:`IOError`
            when no job descriptor files are found
        '''
        batches = dict()
        batches['run'] = list()
        run_job_files = glob.glob(
            os.path.join(self.batches_location, '*_run_*.batch.json')
        )
        if not run_job_files:
            raise IOError('No batch files found.')
        collect_job_files = glob.glob(
            os.path.join(self.batches_location, '*_collect.batch.json')
        )

        for f in run_job_files:
            batch = self._read_batch_file(f)
            batches['run'].append(batch)
        if collect_job_files:
            f = collect_job_files[0]
            batches['collect'] = self._read_batch_file(f)

        return batches

    def get_log_output_from_files(self, phase, job_id=None):
        '''Gets log outputs (standard output and error) from files.

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
                os.path.join(self.log_location, '*_run*_%.6d*.out' % job_id)
            )
            stderr_files = glob.glob(
                os.path.join(self.log_location, '*_run*_%.6d*.err' % job_id)
            )
            if not stdout_files or not stderr_files:
                raise IOError('No log files found for run job # %d' % job_id)
        else:
            stdout_files = glob.glob(
                os.path.join(self.log_location, '*_%s*.out' % phase)
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
        '''Builds the path to a batch file for a run job.

        Parameters
        ----------
        job_id: int
            one-based job identifier number

        Returns
        -------
        str
            absolute path to the file that holds the description of the
            job with the given `job_id`

        Note
        ----
        The total number of jobs is limited to 10^6.
        '''
        return os.path.join(
            self.batches_location,
            '%s_run_%.6d.batch.json' % (self.step_name, job_id)
        )

    def _build_batch_filename_for_collect_job(self):
        '''Builds the path to a batch file for a "collect" job.

        Returns
        -------
        str
            absolute path to the file that holds the description of the
            job with the given `job_id`
        '''
        return os.path.join(
            self.batches_location,
            '%s_collect.batch.json' % self.step_name
        )

    def get_run_batch(self, job_id):
        '''Get description for a "run" job.

        Parameters
        ----------
        job_id: int
            one-based job identifier

        Returns
        -------
        Dict[str, Union[int, str, list, dict]]
            job description
        '''
        batch_filename = self._build_batch_filename_for_run_job(job_id)
        return self._read_batch_file(batch_filename)

    def get_collect_batch(self):
        '''Get description for a "collect" job.

        Returns
        -------
        Dict[str, Union[int, str, list, dict]]
            job description
        '''
        batch_filename = self._build_batch_filename_for_collect_job()
        return self._read_batch_file(batch_filename)

    def store_batches(self, batches):
        '''Persists job descriptions on disk.

        Parameters
        ----------
        batches: List[Dict[str, Union[int, str, list, dict]]]
            job descriptions
        '''
        self._write_batch_files(batches)

    def _read_batch_file(self, filename):
        '''Reads job description from JSON file.

        Parameters
        ----------
        filename: str
            absolute path to the file that contains the description
            of a single job

        Returns
        -------
        dict
            batch

        Raises
        ------
        OSError
            when `filename` does not exist
        '''
        if not os.path.exists(filename):
            raise OSError(
                'Job description file does not exist: %s.\n'
                'Initialize the step first by calling the "init" method.'
                % filename
            )
        with JsonReader(filename) as f:
            batch = f.read()
        return batch

    def _write_batch_files(self, batches):
        '''Writes job descriptions to files in JSON format.

        Parameters
        ----------
        batches: List[dict]
            job descriptions

        Note
        ----
        The paths for "inputs" and "outputs" are made relative to the
        experiment directory.
        '''
        for i, batch in enumerate(batches['run']):
            batch_file = self._build_batch_filename_for_run_job(i+1)
            with JsonWriter(batch_file) as f:
                f.write(batch)
        if 'collect' in batches.keys():
            batch = batches['collect']
            batch_file = self._build_batch_filename_for_collect_job()
            with JsonWriter(batch_file) as f:
                f.write(batch)

    def _build_init_command(self, batch_args):
        logger.debug('build "init" command')
        command = [self.step_name]
        command.extend(['-v' for x in range(self.verbosity)])
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

    def _build_run_command(self, job_id):
        logger.debug('build "run" command')
        command = [self.step_name]
        command.extend(['-v' for x in range(self.verbosity)])
        command.append(self.experiment_id)
        command.extend(['run', '--job', str(job_id)])
        return command

    def _build_collect_command(self):
        logger.debug('build "collect" command')
        command = [self.step_name]
        command.extend(['-v' for x in range(self.verbosity)])
        command.append(self.experiment_id)
        command.extend(['collect'])
        return command

    @abstractmethod
    def run_job(self, batch):
        '''Runs an individual job.

        Parameters
        ----------
        batch: dict
            description of the job
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
    def create_batches(self, args):
        '''Creates job descriptions with information required for
        processing of individual batch jobs.

        Job descriptions need to be provided for the following phases:

            * *run*: collection of tasks that are processed in parallel
            * *collect* (optional): a single task that may be processed
              after the *run* phase, for exmample for the aggregation of outputs

        Each batch is a mapping that must provide at least the following
        key-value pair:

            * "id": one-based job identifier number (*int*)

        Additional key-value pairs may be provided, depending on the
        requirements of the step. In case a *collect* phase is implemented for
        the step, the corresponding batch may provide additional key-value pairs.

        A minimal job description has the following structure::

            {
                "run": [
                    {
                        "id": 1
                    },
                    ...
                ]
                "collect": {}
            }

        Parameters
        ----------
        args: tmlib.args.Args
            an instance of an implemented subclass of the `Args` base class

        Returns
        -------
        Dict[str, Union[List[dict], dict]]
            job descriptions
        '''
        pass

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

    def create_run_job_collection(self, submission_id):
        '''Creates a job collection for the "run" phase of the step.

        Parameters
        ----------
        submission_id: int
            ID of the corresponding
            :class:`Submission <tmlib.models.submission.Submission>`

        Returns
        -------
        tmlib.workflow.job.SingleRunJobCollection
            collection of "run" jobs
        '''
        return SingleRunJobCollection(
            step_name=self.step_name, submission_id=submission_id,
            output_dir=self.log_location
        )

    def create_run_jobs(self, submission_id, user_name, job_collection, batches,
            duration, memory, cores):
        '''Creates jobs for the parallel "run" phase of the step.

        Parameters
        ----------
        submission_id: int
            ID of the corresponding submission
        user_name: str
            name of the submitting user
        job_collection: tmlib.workflow.job.SingleRunJobCollection
            empty collection of *run* jobs that should be populated
        batches: List[dict]
            job descriptions
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
        tmlib.workflow.jobs.SingleRunJobCollection
            run jobs
        '''
        logger.info('create "run" jobs for submission %d', submission_id)
        logger.debug('allocated time for run jobs: %s', duration)
        logger.debug('allocated memory for run jobs: %d MB', memory)
        logger.debug('allocated cores for run jobs: %d', cores)

        for b in batches:
            job = RunJob(
                step_name=self.step_name,
                arguments=self._build_run_command(job_id=b['id']),
                output_dir=self.log_location,
                job_id=b['id'],
                submission_id=submission_id,
                user_name=user_name
            )
            job.requested_walltime = Duration(duration)
            job.requested_memory = Memory(memory, Memory.MB)
            job.requested_cores = cores
            job_collection.add(job)
        return job_collection

    def create_init_job(self, submission_id, user_name, batch_args,
            duration='12:00:00'):
        '''Creates job for the "init" phase of the step.

        Parameters
        ----------
        submission_id: int
            ID of the corresponding submission
        user_name: str
            name of the submitting user
        batch_args: tmlib.workflow.args.BatchArguments
            step-specific implementation of
            :class:`BatchArguments <tmlib.workflow.args.BatchArguments>`
        duration: str, optional
            computational time that should be allocated for the job
            in HH:MM:SS format (default: ``"12:00:00"``)

        Returns
        -------
        tmlib.workflow.jobs.InitJob
            init job

        '''
        logger.info('create "init" job for submission %d', submission_id)
        logger.debug('allocated time for "init" job: %s', duration)
        logger.debug('allocated memory for "init" job: %d MB', cfg.cpu_memory)
        logger.debug('allocated cores for "init" job: %d', cfg.cpu_cores)
        job = InitJob(
            step_name=self.step_name,
            arguments=self._build_init_command(batch_args),
            output_dir=self.log_location,
            submission_id=submission_id,
            user_name=user_name
        )
        job.requested_walltime = Duration(duration)
        job.requested_memory = Memory(cfg.cpu_memory, Memory.MB)
        job.requested_cores = cfg.cpu_cores
        return job

    def create_collect_job(self, submission_id, user_name, duration='06:00:00'):
        '''Creates job for the "collect" phase of the step.

        Parameters
        ----------
        submission_id: int
            ID of the corresponding submission
        user_name: str
            name of the submitting user
        duration: str, optional
            computational time that should be allocated for a single job;
            in HH:MM:SS format (default: ``"06:00:00"``)

        Returns
        -------
        tmlib.workflow.jobs.CollectJob
            collect job

        '''
        logger.info('create "collect" job for submission %d', submission_id)
        logger.debug('allocated time for "collect" job: %s', duration)
        logger.debug('allocated memory for "collect" job: %d MB', cfg.cpu_memory)
        logger.debug('allocated cores for "collect" job: %d', cfg.cpu_cores)
        job = CollectJob(
            step_name=self.step_name,
            arguments=self._build_collect_command(),
            output_dir=self.log_location,
            submission_id=submission_id,
            user_name=user_name
        )
        job.requested_walltime = Duration(duration)
        job.requested_memory = Memory(cfg.cpu_memory, Memory.MB)
        job.requested_cores = cfg.cpu_cores
        return job

