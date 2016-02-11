import os
import yaml
import glob
import time
import logging
import shutil
from natsort import natsorted
from abc import ABCMeta
from abc import abstractmethod
from abc import abstractproperty
from cached_property import cached_property
import gc3libs
from gc3libs.quantity import Duration
from gc3libs.quantity import Memory
from gc3libs.session import Session
from gc3libs.workflow import TaskCollection

from . import utils
from .readers import JsonReader
from .writers import JsonWriter
from .errors import JobDescriptionError
from .cluster_utils import format_stats_data
from .cluster_utils import get_task_data
from .cluster_utils import print_task_status
from .cluster_utils import log_task_failure
from .jobs import RunJob
from .jobs import RunJobCollection
from .jobs import CollectJob
from .tmaps.workflow import WorkflowStep

logger = logging.getLogger(__name__)


class BasicClusterRoutines(object):

    __metaclass__ = ABCMeta

    def __init__(self, experiment):
        '''
        Initialize an instance of class ClusterRoutines.

        Parameters
        ----------
        experiment: tmlib.experiment.Experiment
            configured experiment object
        '''
        self.experiment = experiment

    @abstractproperty
    def project_dir(self):
        pass

    @cached_property
    def log_dir(self):
        '''
        Returns
        -------
        str
            directory where log files are stored

        Note
        ----
        The directory is created if it doesn't exist.
        '''
        self._log_dir = os.path.join(self.project_dir, 'log')
        if not os.path.exists(self._log_dir):
            logger.debug('create output directory for log files: %s',
                         self._log_dir)
            os.mkdir(self._log_dir)
        return self._log_dir

    @property
    def session_dir(self):
        '''
        Returns
        -------
        str
            directory for a
            `GC3Pie Session <http://gc3pie.readthedocs.org/en/latest/programmers/api/gc3libs/session.html>`_
        '''
        return os.path.join(self.project_dir, 'cli_session')

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

    @staticmethod
    def _create_batches(li, n):
        # Create a list of lists from a list, where each sublist has length n
        n = max(1, n)
        return [li[i:i + n] for i in range(0, len(li), n)]

    @staticmethod
    def log_task_data(task_data, monitoring_depth):
        return print_task_status(task_data, monitoring_depth)

    @staticmethod
    def log_task_failure(task_data):
        return log_task_failure(task_data, logger)

    def create_session(self, overwrite=True, backup=False):
        '''
        Create a `GC3Pie session <http://gc3pie.readthedocs.org/en/latest/programmers/api/gc3libs/session.html>`_
        for job persistence.

        Parameters
        ----------
        overwrite: bool, optional
            overwrite an existing session (default: ``True``)
        backup: bool, optional
            backup an existing session (default: ``False``)

        Note
        ----
        If `backup` or `overwrite` are set to ``True`` a new session will be
        created, otherwise a session existing from a previous submission
        will be re-used.
        '''
        logger.info('create session')
        if overwrite:
            if os.path.exists(self.session_dir):
                logger.debug('remove session directory: %s', self.session_dir)
                shutil.rmtree(self.session_dir)
        if backup:
            current_time = self.create_datetimestamp()
            backup_dir = '%s_%s' % (self.session_dir, current_time)
            logger.debug('create backup of session directory: %s', backup_dir)
            shutil.move(self.session_dir, backup_dir)
        return Session(self.session_dir)

    def submit_jobs(self, session, monitoring_interval=5, monitoring_depth=1,
                    n_submit=2000):
        '''
        Create a GC3Pie engine that submits jobs to a cluster
        and continuously monitor the progress of jobs.

        Parameters
        ----------
        session: gc3libs.session.Session
            session with jobs that should be submitted
        monitoring_interval: int, optional
            monitoring interval in seconds (default: ``5``)
        monitoring_depth: int, optional
            recursion depth for job monitoring, i.e. in which detail subtasks
            in the task tree should be monitored (default: ``1``)
        n_submit: int, optional
            number of jobs that will be submitted at once (default: ``2000``)

        Returns
        -------
        dict
            information about each job

        Note
        ----
        Jobs are not persistent. Once you cancel the program, all information
        about jobs is lost and you cannot resume the submission.
        '''
        logger.debug('monitoring interval: %d seconds' % monitoring_interval)

        if monitoring_depth < 0:
            monitoring_depth = 0
        logger.debug('monitoring depth: %d' % monitoring_depth)

        # Create an `Engine` instance for running jobs in parallel
        logger.debug('create engine')
        e = gc3libs.create_engine()
        # Put all output files in the same directory
        logger.debug('store stdout/stderr in common output directory')
        e.retrieve_overwrites = True
        # Limit the total number of jobs that can be submitted simultaneously
        e.max_submitted = n_submit
        e.max_in_flight = n_submit
        logger.debug('set maximum number of submitted jobs to %d',
                     e.max_submitted)

        # Add jobs in session to engine instance
        logger.debug('add jobs to engine')
        if not isinstance(session, Session):
            raise TypeError(
                    'Argument "session" must be a GC3Pie session object.')
        e._store = session.store
        task_ids = session.list_ids()
        if len(task_ids) != 1:
            raise ValueError('Session should only contain a single task.')
        logger.debug('add task "%s" to engine', task_ids[-1])
        task = session.load(task_ids[-1])
        # NOTE: This changes the id of the object!
        if not isinstance(task, TaskCollection):
            raise TypeError(
                    'The session should contain a '
                    'gc3libs.workflow.TaskCollection')
        logger.debug('add task %s to engine', task)
        e.add(task)

        # periodically check the status of submitted jobs
        try:
            break_next = False
            while True:

                time.sleep(monitoring_interval)
                logger.debug('wait %d seconds', monitoring_interval)

                logger.info('progress ...')
                e.progress()

                task_data = get_task_data(task)

                self.log_task_data(task_data, monitoring_depth)

                if break_next:
                    break

                # break out of the loop when all jobs are done
                stats = format_stats_data(e.stats())
                if stats['count_total'] > 0:
                    if (stats['count_terminated'] == stats['count_total'] and
                            stats['exitcode'] is not None):
                        break_next = True
                        e.progress()

        except KeyboardInterrupt:
            # User interrupted process, which should kill all running jobs
            # TODO: stop them so that we can resume later
            logger.info('killing jobs')
            logger.debug('killing task %s', task)
            e.kill(task)
            e.progress()

        task_data = get_task_data(task)
        self.log_task_failure(task_data)

        return task_data


class ClusterRoutines(BasicClusterRoutines):

    '''
    Abstract base class for API classes.

    It provides methods for standard cluster routines,
    such as creation and submission of jobs.
    '''

    __metaclass__ = ABCMeta

    def __init__(self, experiment, prog_name, verbosity):
        '''
        Initialize an instance of class ClusterRoutines.

        Parameters
        ----------
        experiment: tmlib.experiment.Experiment
            configured experiment object
        prog_name: str
            name of the corresponding program (command line interface)
        verbosity: int
            logging level

        Returns
        -------
        tmlib.api.ClusterRoutines
        '''
        super(ClusterRoutines, self).__init__(experiment)
        self.experiment = experiment
        self.prog_name = prog_name
        self.verbosity = verbosity

    @cached_property
    def project_dir(self):
        '''
        Returns
        -------
        str
            directory where *.job* files and log output will be stored
        '''
        project_dir = os.path.join(self.experiment.dir,
                                         'tmaps', self.prog_name)
        if not os.path.exists(project_dir):
            logger.debug('create project directory: %s' % project_dir)
            os.makedirs(project_dir)
        return project_dir

    @cached_property
    def job_descriptions_dir(self):
        '''
        Returns
        -------
        str
            directory where job description files are stored
        '''
        self._job_descriptions_dir = os.path.join(self.project_dir,
                                                  'job_descriptions')
        if not os.path.exists(self._job_descriptions_dir):
            logger.debug('create directory for job descriptor files: %s'
                         % self._job_descriptions_dir)
            os.mkdir(self._job_descriptions_dir)
        return self._job_descriptions_dir

    def get_job_descriptions_from_files(self):
        '''
        Get job descriptions from files and combine them into
        the format required by the `create_jobs()` method.

        Returns
        -------
        dict
            job descriptions

        Raises
        ------
        :py:exc:`tmlib.errors.JobDescriptionError`
            when no job descriptor files are found
        '''
        directory = self.job_descriptions_dir
        job_descriptions = dict()
        job_descriptions['run'] = list()
        run_job_files = glob.glob(os.path.join(
                                  directory, '*_run_*.job.json'))
        if not run_job_files:
            raise JobDescriptionError('No job descriptor files found.')
        collect_job_files = glob.glob(os.path.join(
                                      directory, '*_collect.job.json'))

        for f in run_job_files:
            batch = self.read_job_file(f)
            job_descriptions['run'].append(batch)
        if collect_job_files:
            f = collect_job_files[0]
            job_descriptions['collect'] = self.read_job_file(f)

        return job_descriptions

    def get_log_output_from_files(self, job_id):
        '''
        Get log outputs (standard output and error) from files.

        Parameters
        ----------
        job_id: int
            one-based job identifier number

        Returns
        -------
        Dict[str, str]
            "stdout" and "stderr" for the given job

        Note
        ----
        In case there are several log files present for the given the most
        recent one will be used (sorted by submission date and time point).
        '''

        directory = self.log_dir
        if job_id is not None:
            stdout_files = glob.glob(os.path.join(
                                     directory, '*_run*_%.6d_*.out' % job_id))
            stderr_files = glob.glob(os.path.join(
                                     directory, '*_run*_%.6d_*.err' % job_id))
            if not stdout_files or not stderr_files:
                raise IOError('No log files found for run job # %d' % job_id)
        else:
            stdout_files = glob.glob(os.path.join(
                                     directory, '*_collect_*.out'))
            stderr_files = glob.glob(os.path.join(
                                     directory, '*_collect_*.err'))
            if not stdout_files or not stderr_files:
                raise IOError('No log files found for collect job')
        # Take the most recent log files
        log = dict()
        with open(natsorted(stdout_files)[-1], 'r') as f:
            log['stdout'] = f.read()
        with open(natsorted(stderr_files)[-1], 'r') as f:
            log['stderr'] = f.read()
        return log

    def list_output_files(self, job_descriptions):
        '''
        Provide a list of all output files that should be created by the
        program.

        Parameters
        ----------
        job_descriptions: List[dict]
            job descriptions
        '''
        files = list()
        if job_descriptions['run']:
            run_files = utils.flatten([
                j['outputs'].values() for j in job_descriptions['run']
            ])
            if all([isinstance(f, list) for f in run_files]):
                run_files = utils.flatten(run_files)
                if all([isinstance(f, list) for f in run_files]):
                    run_files = utils.flatten(run_files)
                files.extend(run_files)
            else:
                files.extend(run_files)
        if 'collect' in job_descriptions.keys():
            outputs = job_descriptions['collect']['outputs']
            collect_files = utils.flatten(outputs.values())
            if all([isinstance(f, list) for f in collect_files]):
                collect_files = utils.flatten(collect_files)
                if all([isinstance(f, list) for f in collect_files]):
                    collect_files = utils.flatten(collect_files)
                files.extend(collect_files)
            else:
                files.extend(collect_files)
            if 'removals' in job_descriptions['collect']:
                for k in job_descriptions['collect']['removals']:
                    for f in job_descriptions['collect']['inputs'][k]:
                        if isinstance(f, list):
                            [files.remove(x) for x in f]
                        else:
                            files.remove(f)
        return files

    def list_input_files(self, job_descriptions):
        '''
        Provide a list of all input files that are required by the program.

        Parameters
        ----------
        job_descriptions: List[dict]
            job descriptions
        '''
        files = list()
        if job_descriptions['run']:
            run_files = utils.flatten([
                j['inputs'].values() for j in job_descriptions['run']
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

    def build_run_job_filename(self, job_id):
        '''
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
                    self.job_descriptions_dir,
                    '%s_run_%.6d.job.json' % (self.prog_name, job_id))

    def build_collect_job_filename(self):
        '''
        Returns
        -------
        str
            absolute path to the file that holds the description of the
            job with the given `job_id`
        '''
        return os.path.join(
                    self.job_descriptions_dir,
                    '%s_collect.job.json' % self.prog_name)

    def _make_paths_absolute(self, batch):
        for key, value in batch['inputs'].items():
            if isinstance(value, dict):
                for k, v in batch['inputs'][key].items():
                    if isinstance(v, list):
                        batch['inputs'][key][k] = [
                            os.path.join(self.experiment.dir, sub_v)
                            for sub_v in v
                        ]
                    else:
                        batch['inputs'][key][k] = \
                            os.path.join(self.experiment.dir, v)
            elif isinstance(value, list):
                if len(value) == 0:
                    continue
                if isinstance(value[0], list):
                    for i, v in enumerate(value):
                        batch['inputs'][key][i] = [
                            os.path.join(self.experiment.dir, sub_v)
                            for sub_v in v
                        ]
                else:
                    batch['inputs'][key] = [
                        os.path.join(self.experiment.dir, v) for v in value
                    ]
            else:
                raise TypeError(
                        'Value of "inputs" must have type list or dict.')
        for key, value in batch['outputs'].items():
            if isinstance(value, list):
                if len(value) == 0:
                    continue
                if isinstance(value[0], list):
                    for i, v in enumerate(value):
                        batch['outputs'][key][i] = [
                            os.path.join(self.experiment.dir, sub_v)
                            for sub_v in v
                        ]
                else:
                    batch['outputs'][key] = [
                        os.path.join(self.experiment.dir, v)
                        for v in value
                    ]
            elif isinstance(value, basestring):
                batch['outputs'][key] = \
                    os.path.join(self.experiment.dir, value)
            else:
                raise TypeError(
                        'Value of "outputs" must have type list or str.')
        return batch

    def read_job_file(self, filename):
        '''
        Read job description from JSON file.

        Parameters
        ----------
        filename: str
            absolute path to the *.job* file that contains the description
            of a single job

        Returns
        -------
        dict
            job description (batch)

        Raises
        ------
        OSError
            when `filename` does not exist

        Note
        ----
        The relative paths for "inputs" and "outputs" are made absolute.
        '''
        with JsonReader() as reader:
            batch = reader.read(filename)
            return self._make_paths_absolute(batch)

    @staticmethod
    def _check_io_description(job_descriptions):
        if not all([
                isinstance(batch['inputs'], dict)
                for batch in job_descriptions['run']]):
            raise TypeError('"inputs" must have type dictionary')
        if not all([
                isinstance(batch['inputs'].values(), list)
                for batch in job_descriptions['run']]):
            raise TypeError('Elements of "inputs" must have type list')
        if not all([
                isinstance(batch['outputs'], dict)
                for batch in job_descriptions['run']]):
            raise TypeError('"outputs" must have type dictionary')
        if not all([
                all([isinstance(o, list) for o in batch['outputs'].values()])
                for batch in job_descriptions['run']]):
            raise TypeError('Elements of "outputs" must have type list.')
        if 'collect' in job_descriptions:
            batch = job_descriptions['collect']
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
                            os.path.relpath(sub_v, self.experiment.dir)
                            for sub_v in v
                        ]
                    else:
                        batch['inputs'][key][k] = \
                            os.path.relpath(v, self.experiment.dir)
            elif isinstance(value, list):
                if len(value) == 0:
                    continue
                if isinstance(value[0], list):
                    for i, v in enumerate(value):
                        batch['inputs'][key][i] = [
                            os.path.relpath(sub_v, self.experiment.dir)
                            for sub_v in v
                        ]
                else:
                    batch['inputs'][key] = [
                        os.path.relpath(v, self.experiment.dir)
                        for v in value
                    ]
            else:
                raise TypeError(
                        'Value of "inputs" must have type list or dict.')
        for key, value in batch['outputs'].items():
            if isinstance(value, list):
                if len(value) == 0:
                    continue
                if isinstance(value[0], list):
                    for i, v in enumerate(value):
                        batch['outputs'][key][i] = [
                            os.path.relpath(sub_v, self.experiment.dir)
                            for sub_v in v
                        ]
                else:
                    batch['outputs'][key] = [
                        os.path.relpath(v, self.experiment.dir)
                        for v in value
                    ]
            elif isinstance(value, basestring):
                batch['outputs'][key] = \
                    os.path.relpath(value, self.experiment.dir)
            else:
                raise TypeError(
                        'Value of "outputs" must have type list or str.')
        return batch

    def write_job_files(self, job_descriptions):
        '''
        Write job descriptions to files as JSON.

        Parameters
        ----------
        job_descriptions: List[dict]
            job descriptions

        Note
        ----
        The paths for "inputs" and "outputs" are made relative to the
        experiment directory.
        '''
        if not os.path.exists(self.job_descriptions_dir):
            logger.debug('create directories for job descriptor files')
            os.makedirs(self.job_descriptions_dir)
        self._check_io_description(job_descriptions)

        with JsonWriter() as writer:
            for batch in job_descriptions['run']:
                logger.debug('make paths relative to experiment directory')
                batch = self._make_paths_relative(batch)
                job_file = self.build_run_job_filename(batch['id'])
                writer.write(job_file, batch)
            if 'collect' in job_descriptions.keys():
                batch = self._make_paths_relative(job_descriptions['collect'])
                job_file = self.build_collect_job_filename()
                writer.write(job_file, batch)

    def _build_run_command(self, batch):
        # Build a command for GC3Pie submission. For further information on
        # the structure of the command see documentation of subprocess package:
        # https://docs.python.org/2/library/subprocess.html.
        job_id = batch['id']
        command = [self.prog_name]
        command.extend(['-v' for x in xrange(self.verbosity)])
        command.append(self.experiment.dir)
        command.extend(['run', '--job', str(job_id)])
        return command

    def _build_collect_command(self):
        command = [self.prog_name]
        command.extend(['-v' for x in xrange(self.verbosity)])
        command.append(self.experiment.dir)
        command.extend(['collect'])
        return command

    @abstractmethod
    def run_job(self, batch):
        '''
        Run an individual job.

        Parameters
        ----------
        batch: dict
            description of the job
        '''
        pass

    @abstractmethod
    def collect_job_output(self, batch):
        '''
        Collect the output of jobs and fuse them if necessary.

        Parameters
        ----------
        job_descriptions: List[dict]
            job descriptions
        **kwargs: dict
            additional variable input arguments as key-value pairs
        '''
        pass

    @abstractmethod
    def create_job_descriptions(self, args):
        '''
        Create job descriptions with information required for the creation and
        processing of individual jobs.

        Parameters
        ----------
        args: tmlib.args.Args
            an instance of an implemented subclass of the `Args` base class

        There are two phases:
            * *run* phase: collection of tasks that are processed in parallel
            * *collect* phase: a single task that is processed once the
              *run* phase is terminated successfully

        Each batch (element of the *run* job_descriptions) must provide the
        following key-value pairs:
            * "id": one-based job identifier number (*int*)
            * "inputs": absolute paths to input files required to run the job
              (Dict[*str*, List[*str*]])
            * "outputs": absolute paths to output files produced the job
              (Dict[*str*, List[*str*]])

        In case a *collect* job is required, the corresponding batch must
        provide the following key-value pairs:
            * "inputs": absolute paths to input files required to collect job
              output of the *run* phase (Dict[*str*, List[*str*]])
            * "outputs": absolute paths to output files produced by the job
              (Dict[*str*, List[*str*]])

        A *collect* job description can have the optional key "removals", which
        provides a list of strings indicating which of the inputs are removed
        during the *collect* phase.

        A complete job_descriptions has the following structure::

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
                        "removals":        # set
                    }
            }

        Returns
        -------
        Dict[str, List[dict] or dict]
            job descriptions
        '''
        pass

    @abstractmethod
    def apply_statistics(self, output_dir, plates, wells, sites, channels,
                         tpoints, zplanes, **kwargs):
        '''
        Apply the calculated statistics to images.

        Parameters
        ----------
        output_dir: str
            absolute path to directory where the processed images should be
            stored
        plates: List[str]
            plate names
        wells: List[str]
            well identifiers
        sites: List[int]
            site indices
        channels: List[str]
            channel indices
        tpoints: List[int]
            time point (cycle) indices
        zplanes: List[int]
            z-plane indices
        **kwargs: dict
            additional variable input arguments as key-value pairs
        '''
        pass

    def print_job_descriptions(self, job_descriptions):
        '''
        Print `job_descriptions` to standard output in YAML format.

        Parameters
        ----------
        job_descriptions: Dict[List[dict]]
            description of inputs and outputs or individual jobs
        '''
        print yaml.safe_dump(job_descriptions, default_flow_style=False)

    def create_jobs(self, job_descriptions,
                    duration=None, memory=None, cores=None):
        '''
        Create jobs that can be submitted for processing.

        Parameters
        ----------
        job_descriptions: Dict[List[dict]]
            description of inputs and outputs of individual computational jobs
        duration: str, optional
            computational time that should be allocated for a single job;
            in HH:MM:SS format (default: ``None``)
        memory: int, optional
            amount of memory in Megabyte that should be allocated for a single
            job (default: ``None``)
        cores: int, optional
            number of CPU cores that should be allocated for a single job
            (default: ``None``)

        Returns
        -------
        tmlib.tmaps.workflow.WorkflowStep
            collection of jobs
        '''
        logger.info('create workflow step')

        if 'run' in job_descriptions.keys():
            logger.info('create jobs for "run" phase')
            run_jobs = RunJobCollection(self.prog_name)
            for i, batch in enumerate(job_descriptions['run']):

                job = RunJob(
                        step_name=self.prog_name,
                        arguments=self._build_run_command(batch),
                        output_dir=self.log_dir,
                        job_id=batch['id']
                )
                if duration:
                    job.requested_walltime = Duration(duration)
                if memory:
                    job.requested_memory = Memory(memory, Memory.GB)
                if cores:
                    if not isinstance(cores, int):
                        raise TypeError('Argument "cores" must have type int.')
                    if not cores > 0:
                        raise ValueError('The value of "cores" must be positive.')
                    job.requested_cores = cores

                run_jobs.add(job)

        else:
            run_jobs = None

        if 'collect' in job_descriptions.keys():
            logger.info('create job for "collect" phase')
            batch = job_descriptions['collect']

            collect_job = CollectJob(
                    step_name=self.prog_name,
                    arguments=self._build_collect_command(),
                    output_dir=self.log_dir
            )
            collect_job.requested_walltime = Duration('01:00:00')
            collect_job.requested_memory = Memory(4, Memory.GB)

        else:
            collect_job = None

        jobs = WorkflowStep(
                    name=self.prog_name,
                    run_jobs=run_jobs,
                    collect_job=collect_job
        )

        return jobs
