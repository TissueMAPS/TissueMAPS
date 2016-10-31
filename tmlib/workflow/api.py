# TmLibrary - TissueMAPS library for distibuted image processing routines.
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
from gc3libs.quantity import Duration
from gc3libs.quantity import Memory

import tmlib.models as tm
from tmlib import utils
from tmlib.readers import JsonReader
from tmlib.writers import JsonWriter
from tmlib.errors import JobDescriptionError
from tmlib.errors import WorkflowError
from tmlib.errors import WorkflowDescriptionError
from tmlib.errors import WorkflowTransitionError
from tmlib.workflow import get_step_args
from tmlib.workflow.jobs import InitJob
from tmlib.workflow.jobs import RunJob
from tmlib.workflow.jobs import SingleRunJobCollection
from tmlib.workflow.jobs import CollectJob
from tmlib.workflow import WorkflowStep

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

    '''Abstract base class for submission of jobs to a cluster.'''

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

    The metaclass inspects the method `collect_job_output` of derived classes
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
    :func:`tmlib.workflow.register_api` to register it for use
    within a worklow.

    Note
    ----
    Classes that don't implement the *collect* phase must decorate the
    implemented `collect_job_output` method with
    :func:`tmlib.utils.notimplemented`.
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
            self.workflow_location = experiment.workflow_location

    @property
    def step_name(self):
        '''str: name of the step'''
        return self.__module__.split('.')[-2]

    @staticmethod
    def _create_batches(li, n):
        # Create a list of lists from a list, where each sublist has length n
        n = max(1, n)
        return [li[i:i + n] for i in range(0, len(li), n)]

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
            batch = self.read_batch_file(f)
            batches['run'].append(batch)
        if collect_job_files:
            f = collect_job_files[0]
            batches['collect'] = self.read_batch_file(f)

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

    def list_output_files(self, batches):
        '''Lists all output files that should be created by the step.

        Parameters
        ----------
        batches: List[dict]
            job descriptions
        '''
        files = list()
        if batches['run']:
            run_files = utils.flatten([
                self._make_paths_absolute(j)['outputs'].values()
                for j in batches['run']
            ])
            if all([isinstance(f, list) for f in run_files]):
                run_files = utils.flatten(run_files)
                if all([isinstance(f, list) for f in run_files]):
                    run_files = utils.flatten(run_files)
                files.extend(run_files)
            else:
                files.extend(run_files)
        if 'collect' in batches.keys():
            outputs = batches['collect']['outputs']
            collect_files = utils.flatten(outputs.values())
            if all([isinstance(f, list) for f in collect_files]):
                collect_files = utils.flatten(collect_files)
                if all([isinstance(f, list) for f in collect_files]):
                    collect_files = utils.flatten(collect_files)
                files.extend(collect_files)
            else:
                files.extend(collect_files)
        return files

    def list_input_files(self, batches):
        '''Provides a list of all input files that are required by the step.

        Parameters
        ----------
        batches: List[dict]
            job descriptions
        '''
        files = list()
        if batches['run']:
            run_files = utils.flatten([
                self._make_paths_absolute(j)['inputs'].values()
                for j in batches['run']
            ])
            if all([isinstance(f, list) for f in run_files]):
                run_files = utils.flatten(run_files)
                if all([isinstance(f, list) for f in run_files]):
                    run_files = utils.flatten(run_files)
                files.extend(run_files)
            elif any([isinstance(f, dict) for f in run_files]):
                files.extend(utils.flatten([
                    utils.flatten(f.values())
                    for f in run_files if isinstance(f, dict)
                ]))
            else:
                files.extend(run_files)
        return files

    def build_batch_filename_for_run_job(self, job_id):
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

    def build_batch_filename_for_collect_job(self):
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

    def _make_paths_absolute(self, batch):
        for key, value in batch['inputs'].items():
            if isinstance(value, dict):
                for k, v in batch['inputs'][key].items():
                    if isinstance(v, list):
                        batch['inputs'][key][k] = [
                            os.path.join(self.workflow_location, sub_v)
                            for sub_v in v
                        ]
                    else:
                        batch['inputs'][key][k] = os.path.join(
                            self.workflow_location, v
                        )
            elif isinstance(value, list):
                if len(value) == 0:
                    continue
                if isinstance(value[0], list):
                    for i, v in enumerate(value):
                        batch['inputs'][key][i] = [
                            os.path.join(self.workflow_location, sub_v)
                            for sub_v in v
                        ]
                else:
                    batch['inputs'][key] = [
                        os.path.join(self.workflow_location, v)
                        for v in value
                    ]
            else:
                raise TypeError(
                    'Value of "inputs" must have type list or dict.'
                )
        for key, value in batch['outputs'].items():
            if isinstance(value, list):
                if len(value) == 0:
                    continue
                if isinstance(value[0], list):
                    for i, v in enumerate(value):
                        batch['outputs'][key][i] = [
                            os.path.join(self.workflow_location, sub_v)
                            for sub_v in v
                        ]
                else:
                    batch['outputs'][key] = [
                        os.path.join(self.workflow_location, v)
                        for v in value
                    ]
            elif isinstance(value, basestring):
                batch['outputs'][key] = os.path.join(
                    self.workflow_location, value
                )
            else:
                raise TypeError(
                    'Value of "outputs" must have type list or str.'
                )
        return batch

    def read_batch_file(self, filename):
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

        Note
        ----
        The relative paths for "inputs" and "outputs" are made absolute.
        '''
        if not os.path.exists(filename):
            raise OSError(
                'Job description file does not exist: %s.\n'
                'Initialize the step first by calling the "init" method.'
                % filename
            )
        with JsonReader(filename) as f:
            batch = f.read()
        return self._make_paths_absolute(batch)

    @staticmethod
    def _check_io_description(batches):
        if not all([
                isinstance(batch['inputs'], dict)
                for batch in batches['run']]):
            raise TypeError('"inputs" must have type dictionary')
        if not all([
                isinstance(batch['inputs'].values(), list)
                for batch in batches['run']]):
            raise TypeError('Elements of "inputs" must have type list')
        if not all([
                isinstance(batch['outputs'], dict)
                for batch in batches['run']]):
            raise TypeError('"outputs" must have type dictionary')
        if not all([
                all([isinstance(o, list) for o in batch['outputs'].values()])
                for batch in batches['run']]):
            raise TypeError('Elements of "outputs" must have type list.')
        if 'collect' in batches:
            batch = batches['collect']
            if not isinstance(batch['inputs'], dict):
                raise TypeError('"inputs" must have type dictionary')
            if not isinstance(batch['inputs'].values(), list):
                raise TypeError('Elements of "inputs" must have type list')
            if not isinstance(batch['outputs'], dict):
                raise TypeError('"outputs" must have type dictionary')
            if not all([isinstance(o, list) for o in batch['outputs'].values()]):
                raise TypeError('Elements of "outputs" must have type list')

    def _make_paths_relative(self, batch):
        for key, value in batch['inputs'].items():
            if isinstance(value, dict):
                for k, v in batch['inputs'][key].items():
                    if isinstance(v, list):
                        batch['inputs'][key][k] = [
                            os.path.relpath(sub_v, self.workflow_location)
                            for sub_v in v
                        ]
                    else:
                        batch['inputs'][key][k] = os.path.relpath(
                            v, self.workflow_location
                        )
            elif isinstance(value, list):
                if len(value) == 0:
                    continue
                if isinstance(value[0], list):
                    for i, v in enumerate(value):
                        batch['inputs'][key][i] = [
                            os.path.relpath(sub_v, self.workflow_location)
                            for sub_v in v
                        ]
                else:
                    batch['inputs'][key] = [
                        os.path.relpath(v, self.workflow_location)
                        for v in value
                    ]
            else:
                raise TypeError(
                    'Value of "inputs" must have type list or dict.'
                )
        for key, value in batch['outputs'].items():
            if isinstance(value, list):
                if len(value) == 0:
                    continue
                if isinstance(value[0], list):
                    for i, v in enumerate(value):
                        batch['outputs'][key][i] = [
                            os.path.relpath(sub_v, self.workflow_location)
                            for sub_v in v
                        ]
                else:
                    batch['outputs'][key] = [
                        os.path.relpath(v, self.workflow_location)
                        for v in value
                    ]
            elif isinstance(value, basestring):
                batch['outputs'][key] = os.path.relpath(
                    value, self.workflow_location
                )
            else:
                raise TypeError(
                    'Value of "outputs" must have type list or str.'
                )
        return batch

    def write_batch_files(self, batches):
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
        self._check_io_description(batches)
        for batch in batches['run']:
            logger.debug('make paths relative to experiment directory')
            batch = self._make_paths_relative(batch)
            batch_file = self.build_batch_filename_for_run_job(batch['id'])
            with JsonWriter(batch_file) as f:
                f.write(batch)
        if 'collect' in batches.keys():
            batch = self._make_paths_relative(batches['collect'])
            batch_file = self.build_batch_filename_for_collect_job()
            with JsonWriter(batch_file) as f:
                f.write(batch)

    def _build_init_command(self, batch_args, extra_args):
        logger.debug('build "init" command')
        command = [self.step_name]
        command.extend(['-v' for x in xrange(self.verbosity)])
        command.append(self.experiment_id)
        if extra_args is not None:
            for arg in extra_args.iterargs():
                value = getattr(extra_args, arg.name)
                if arg.type == bool:
                    if ((value and not arg.default) or
                        (not value and arg.default)):
                        command.append('--%s' % arg.name)
                else:
                    if value is not None:
                        command.extend(['--%s' % arg.name, str(value)])
        command.append('init')
        for arg in batch_args.iterargs():
            value = getattr(batch_args, arg.name)
            if arg.type == bool:
                if ((value and not arg.default) or
                    (not value and arg.default)):
                    command.append('--%s' % arg.name)
            else:
                if value is not None:
                    command.extend(['--%s' % arg.name, str(value)])
        return command

    def _build_run_command(self, job_id):
        logger.debug('build "run" command')
        command = [self.step_name]
        command.extend(['-v' for x in xrange(self.verbosity)])
        command.append(self.experiment_id)
        command.extend(['run', '--job', str(job_id)])
        return command

    def _build_collect_command(self):
        logger.debug('build "collect" command')
        command = [self.step_name]
        command.extend(['-v' for x in xrange(self.verbosity)])
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
        '''Deletes the output of a previous submission based on the value
        provided by the step-specific implementation of
        :attr:`tmlib.workflow.api.ClusterRoutines.generated_outputs`.
        '''
        with tmlib.utils.ExperimentSession(self.experiment_id) as session:
            if isinstance(self.generated_outputs, dict):
                for obj, ids in self.generated_outputs.iteritems():
                    if _is_model_class(obj):
                        logger.info('remove "%s" outputs', obj.__name__)
                        session.query(obj).\
                            filter(obj.id.in_(ids)).\
                            delete()
                    elif _is_model_class_attr(obj):
                        logger.info(
                            'remove "%s" outputs', obj.__class__.__name__
                        )
                        q = session.query(obj.__class__).\
                            filter(obj.__class__.id.in_(ids))
                        for instance in q:
                            setattr(instance, obj.name, None)
                    else:
                        raise TypeError(
                            'Key "%s" of mapping provided by the'
                            '"generated_outputs" property must be either a '
                            'class derived from tmlib.models.ExperimentModel '
                            'or an attribute of a class derived from '
                            'tmlib.models.ExperimentModel.'
                        )
            elif isinstance(self.generated_outputs, set):
                for obj in self.generated_outputs:
                    if _is_model_class(obj):
                        logger.info('remove "%s" outputs', obj.__name__)
                        session.drop_and_recreate(obj)
                    elif _is_model_class_attr(obj):
                        logger.info(
                            'remove "%s" outputs', obj.__class__.__name__
                        )
                        for instance in session.query(obj.__class__):
                            setattr(instance, obj.name, None)
                    else:
                        raise TypeError(
                            'Elements of the set provided by the '
                            '"generated_outputs" property must be either a '
                            'class derived from tmlib.models.ExperimentModel '
                            'or an attribute of a class derived from '
                            'tmlib.models.ExperimentModel.'
                        )
            else:
                raise TypeError(
                    'The value provided by "generated_outpus" property '
                    'must be either a dictionary or a set.'
                )

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
        '''Creates job descriptions with information required for the creation
        and processing of individual jobs.

        There are three phases:

            * *init*: a single task that asserts the presence of required inputs,
              deletes outputs of previous runs and builds the tasks for the
              subsequent phases
            * *run*: collection of tasks that are processed in parallel
            * *collect* (optional): a single task that may be required to
              aggregate outputs of individual *run* tasks

        Each batch is a mapping that must provide the following key-value pairs:

            * "id": one-based job identifier number (*int*)
            * "inputs": absolute paths to input files required to run the job
              (Dict[*str*, List[*str*]])
            * "outputs": absolute paths to output files produced the job
              (Dict[*str*, List[*str*]])

        In case a *collect* job is required, the corresponding batch must
        provide the following key-value pairs:

            * "inputs": absolute paths to input files required to *collect* job
              output of the *run* phase (Dict[*str*, List[*str*]])
            * "outputs": absolute paths to output files produced by the job
              (Dict[*str*, List[*str*]])

        A *collect* job description can have the optional key "removals", which
        provides a list of strings indicating which of the inputs are removed
        during the *collect* phase.

        A complete batches has the following structure::

            {
                "run": [
                    {
                        "id": ,            # int
                        "inputs": ,        # list or dict,
                        "outputs": ,       # list or dict,
                    },
                    ...
                ]
                "collect":
                    {
                        "inputs": ,        # list or dict,
                        "outputs": ,       # list or dict
                    }
            }

        Parameters
        ----------
        args: tmlib.args.Args
            an instance of an implemented subclass of the `Args` base class

        Returns
        -------
        Dict[str, List[dict] or dict]
            job descriptions
        '''
        pass

    def print_job_descriptions(self, batches):
        '''Prints `batches` to standard output in YAML format.

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
        '''tmlib.workflow.job.SingleRunJobCollection: collection of "run" jobs
        '''
        return SingleRunJobCollection(
            step_name=self.step_name, submission_id=submission_id
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
            if not isinstance(cores, int):
                raise TypeError(
                    'Argument "cores" must have type int.'
                )
            if not cores > 0:
                raise ValueError(
                    'The value of "cores" must be positive.'
                )
            job.requested_cores = cores
            job_collection.add(job)
        return job_collection

    def create_init_job(self, submission_id, user_name, batch_args,
            extra_args=None, duration='12:00:00', memory=3800, cores=1):
        '''Creates job for the "init" phase of the step.

        Parameters
        ----------
        submission_id: int
            ID of the corresponding submission
        user_name: str
            name of the submitting user
        batch_args: tmlib.workflow.args.BatchArguments
            step-specific implementation of
            :class:`tmlib.workflow.args.BatchArguments`
        batch_args: tmlib.workflow.args.ExtraArguments, optional
            step-specific implementation of
            :class:`tmlib.workflow.args.ExtraArguments`
        duration: str, optional
            computational time that should be allocated for the job
            in HH:MM:SS format (default: ``"12:00:00"``)
        memory: int, optional
            amount of memory in Megabyte that should be allocated for the job
            (default: ``3800``)
        cores: int, optional
            number of CPU cores that should be allocated for the job
            (default: ``1``)

        Returns
        -------
        tmlib.workflow.jobs.InitJob
            init job

        '''
        logger.info('create "init" job for submission %d', submission_id)
        logger.debug('allocated time for "init" job: %s', duration)
        logger.debug('allocated memory for "init" job: %d MB', memory)
        logger.debug('allocated cores for "init" job: %d', cores)
        job = InitJob(
            step_name=self.step_name,
            arguments=self._build_init_command(batch_args, extra_args),
            output_dir=self.log_location,
            submission_id=submission_id,
            user_name=user_name
        )
        job.requested_walltime = Duration(duration)
        job.requested_memory = Memory(memory, Memory.MB)
        if not isinstance(cores, int):
            raise TypeError(
                'Argument "cores" must have type int.'
            )
        if not cores > 0:
            raise ValueError(
                'The value of "cores" must be positive.'
            )
        job.requested_cores = cores
        return job

    def create_collect_job(self, submission_id, user_name,
            duration='06:00:00', memory=3800, cores=1):
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
        memory: int, optional
            amount of memory in Megabyte that should be allocated for a single
            (default: ``3800``)
        cores: int, optional
            number of CPU cores that should be allocated for a single job
            (default: ``1``)

        Returns
        -------
        tmlib.workflow.jobs.CollectJob
            collect job

        '''
        logger.info('create "collect" job for submission %d', submission_id)
        logger.debug('allocated time for "collect" job: %s', duration)
        logger.debug('allocated memory for "collect" job: %d MB', memory)
        logger.debug('allocated cores for "collect" job: %d', cores)
        job = CollectJob(
            step_name=self.step_name,
            arguments=self._build_collect_command(),
            output_dir=self.log_location,
            submission_id=submission_id,
            user_name=user_name
        )
        job.requested_walltime = Duration(duration)
        job.requested_memory = Memory(memory, Memory.MB)
        if not isinstance(cores, int):
            raise TypeError(
                'Argument "cores" must have type int.'
            )
        if not cores > 0:
            raise ValueError(
                'The value of "cores" must be positive.'
            )
        job.requested_cores = cores
        return job

