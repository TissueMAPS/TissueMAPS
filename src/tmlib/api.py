import os
import yaml
import glob
import time
import datetime
from abc import ABCMeta
from abc import abstractmethod
from abc import abstractproperty
from cached_property import cached_property
import gc3libs
from gc3libs.quantity import Duration
from gc3libs.quantity import Memory
from gc3libs.session import Session
from gc3libs.workflow import TaskCollection
from gc3libs.workflow import ParallelTaskCollection
from gc3libs.workflow import SequentialTaskCollection
import logging
from . import utils
from .readers import JsonReader
from .writers import JsonWriter
from .errors import JobDescriptionError
from .cluster_utils import format_stats_data
from .cluster_utils import get_task_data

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
        return os.path.join(self.project_dir, 'session')

    @staticmethod
    def create_datetimestamp():
        '''
        Create datetimestamp in the form "year-month-day_hour:minute:second".
        Returns
        -------
        str
            datetimestamp
        '''
        t = time.time()
        return datetime.datetime.fromtimestamp(t).strftime('%Y-%m-%d_%H-%M-%S')

    @staticmethod
    def create_timestamp():
        '''
        Create timestamp in the form "hour:minute:second".

        Returns
        -------
        str
            timestamp
        '''
        t = time.time()
        return datetime.datetime.fromtimestamp(t).strftime('%H-%M-%S')

    @staticmethod
    def _create_batches(li, n):
        # Create a list of lists from a list, where each sublist has length n
        n = max(1, n)
        return [li[i:i + n] for i in range(0, len(li), n)]

    def submit_jobs(self, jobs, monitoring_interval=5, monitoring_depth=1):
        '''
        Create a GC3Pie engine that submits jobs to a cluster
        for parallel and/or sequential processing and monitors their progress.

        Parameters
        ----------
        jobs: gc3libs.workflow.TaskCollection or gc3libs.session.Session
            jobs that should be submitted
        monitoring_interval: int, optional
            monitoring interval in seconds (default: ``5``)
        monitoring_depth: int, optional
            recursion depth for job monitoring, i.e. in which detail subtasks
            in the task tree should be monitored (default: ``1``)

        Returns
        -------
        dict
            detailed information about each job

        See also
        --------
        :py:meth:`
        '''
        logger.debug('monitoring interval: %d seconds' % monitoring_interval)

        if monitoring_depth < 0:
            monitoring_depth = 0
        logger.debug('monitoring depth: %d' % monitoring_depth)

        def log_task_data(task_data):
            def log_recursive(data, i):
                logger.info('%s: %s (%.2f %%)',
                            data['name'], data['state'],
                            data['percent_done'])
                if i <= monitoring_depth:
                    for subtd in data.get('subtasks', list()):
                        log_recursive(subtd, i+1)
            log_recursive(task_data, 0)

        def log_failure(task_data):
            def log_recursive(data, i):
                for subtd in data.get('subtasks', list()):
                    if subtd['failed']:
                        logger.error('job "%s" failed', subtd['name'])
                    log_recursive(subtd, i+1)
            log_recursive(task_data, 0)

        # Create an `Engine` instance for running jobs in parallel
        logger.debug('create engine')
        e = gc3libs.create_engine()
        # Put all output files in the same directory
        logger.debug('store stdout/stderr in common output directory')
        e.retrieve_overwrites = True
        # Limit the total number of jobs that can be submitted simultaneously
        e.max_submitted = 2000
        e.max_in_flight = 2000
        logger.debug('set maximum number of submitted jobs to %d',
                     e.max_submitted)

        # Add tasks to engine instance
        logger.debug('add jobs to engine')
        if isinstance(jobs, Session):
            e._store = jobs.store
            task_ids = jobs.list_ids()
            if len(task_ids) != 1:
                raise ValueError('Session should only contain a single task.')
            logger.debug('add task "%s" to engine', task_ids[-1])
            task = jobs.load(task_ids[-1])
            e.add(task)
        elif isinstance(jobs, TaskCollection):
            task = jobs
            e.add(task)
        else:
            raise TypeError(
                    'Argument "jobs" must either be a GC3Pie task collection '
                    'or a GC3Pie session.')

        # periodically check the status of submitted jobs
        break_next = False
        while True:

            time.sleep(monitoring_interval)
            logger.debug('wait %d seconds', monitoring_interval)

            logger.info('progress ...')
            e.progress()

            if break_next:
                break

            task_data = get_task_data(task, monitoring_depth)

            log_task_data(task_data)
            logger.info('------------------------------------------')

            # break out of the loop when all jobs are done
            aggregate = format_stats_data(e.stats())
            if aggregate['count_total'] > 0:
                if aggregate['count_terminated'] == aggregate['count_total']:
                    break_next = True

        log_failure(task)

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
        if not collect_job_files:
            logger.debug('no "collect" job descriptor file found')
        with JsonReader() as reader:
            for f in run_job_files:
                batch = reader.read(f)
                job_descriptions['run'].append(batch)
            if collect_job_files:
                job_descriptions['collect'] = reader.read(collect_job_files[0])
        return job_descriptions

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
            collect_files =  \
                utils.flatten(job_descriptions['collect']['outputs'].values())
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
        '''
        with JsonReader() as reader:
            return reader.read(filename)

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
                isinstance(batch['outputs'].values(), list)
                for batch in job_descriptions['run']]):
            raise TypeError('Elements of "outputs" must have type list')
        if 'collect' in job_descriptions:
            batch = job_descriptions['collect']
            if not isinstance(batch['inputs'], dict):
                raise TypeError('"inputs" must have type dictionary')
            if not isinstance(batch['inputs'].values(), list):
                raise TypeError('Elements of "inputs" must have type list')
            if not isinstance(batch['outputs'], dict):
                raise TypeError('"outputs" must have type dictionary')
            if not isinstance(batch['outputs'].values(), list):
                raise TypeError('Elements of "outputs" must have type list')

    def write_job_files(self, job_descriptions):
        '''
        Write job descriptions to files as JSON.

        Parameters
        ----------
        job_descriptions: List[dict]
            job descriptions

        Note
        ----
        Log directory is created if it does not exist.
        '''
        if not os.path.exists(self.job_descriptions_dir):
            logger.debug('create directories for job descriptor files')
            os.makedirs(self.job_descriptions_dir)
        self._check_io_description(job_descriptions)
        logger.debug('write job descriptor files')
        with JsonWriter() as writer:
            for batch in job_descriptions['run']:
                job_file = self.build_run_job_filename(batch['id'])
                writer.write(job_file, batch)
            if 'collect' in job_descriptions.keys():
                job_file = self.build_collect_job_filename()
                writer.write(job_file, job_descriptions['collect'])

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

        There are two kinds of jobs:
            * *run* jobs: collection of tasks that are processed in parallel
            * *collect* job: a single task that is processed once all
              *run* jobs are terminated successfully

        Each batch (element of the *run* job_descriptions) must provide the
        following key-value pairs:
            * "id": one-based job indentifier number (*int*)
            * "inputs": absolute paths to input files required to run the job
              (Dict[*str*, List[*str*]])
            * "outputs": absolute paths to output files produced the job
              (Dict[*str*, List[*str*]])

        In case a *collect* job is required, the corresponding batch must
        provide the following key-value pairs:
            * "inputs": absolute paths to input files required to collect job
              output of the *run* step (Dict[*str*, List[*str*]])
            * "outputs": absolute paths to output files produced by the job
              (Dict[*str*, List[*str*]])

        A *collect* job description can have the optional key "removals", which
        provides a list of strings indicating which of the inputs are removed
        during the *collect* step.

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

    def create_jobs(self, job_descriptions, duration=None, memory=None):
        '''
        Create a GC3Pie task collection of "jobs".

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

        Returns
        -------
        gc3libs.workflow.SequentialTaskCollection
            jobs

        Note
        ----
        A `SequentialTaskCollection` is returned even if there is only one
        parallel task (a collection of jobs that are processed in parallel).
        This is done for consistency so that jobs from different steps can
        be handled the same way and easily be combined into a larger workflow.
        '''
        run_jobs = ParallelTaskCollection(
                        jobname='%s_run' % self.prog_name)

        logger.debug('create run jobs: ParallelTaskCollection')
        for i, batch in enumerate(job_descriptions['run']):

            jobname = '%s_run_%.6d' % (self.prog_name, batch['id'])
            timestamp = self.create_datetimestamp()
            log_out_file = '%s_%s.out' % (jobname, timestamp)
            log_err_file = '%s_%s.err' % (jobname, timestamp)

            # Add individual task to collection
            job = gc3libs.Application(
                    arguments=self._build_run_command(batch),
                    inputs=list(),
                    outputs=list(),
                    output_dir=self.log_dir,
                    jobname=jobname,
                    stdout=log_out_file,
                    stderr=log_err_file
            )
            if duration:
                job.requested_walltime = Duration(duration)
            if memory:
                job.requested_memory = Memory(memory, Memory.GB)
            run_jobs.add(job)

        if 'collect' in job_descriptions.keys():
            logger.debug('create collect job: Application')

            batch = job_descriptions['collect']

            jobname = '%s_collect' % self.prog_name
            timestamp = self.create_datetimestamp()
            log_out_file = '%s_%s.out' % (jobname, timestamp)
            log_err_file = '%s_%s.err' % (jobname, timestamp)

            collect_job = gc3libs.Application(
                    arguments=self._build_collect_command(),
                    inputs=list(),
                    outputs=list(),
                    output_dir=self.log_dir,
                    jobname=jobname,
                    stdout=log_out_file,
                    stderr=log_err_file
            )
            collect_job.requested_walltime = Duration('01:00:00')
            collect_job.requested_memory = Memory(32, Memory.GB)

            logger.debug('add run & collect jobs to SequentialTaskCollection')
            jobs = SequentialTaskCollection(
                        tasks=[run_jobs, collect_job],
                        jobname='%s' % self.prog_name)

            # TODO: time and duration for "collect" jobs

        else:

            logger.debug('add run jobs to SequentialTaskCollection')
            jobs = SequentialTaskCollection(
                        tasks=[run_jobs],
                        jobname='%s' % self.prog_name)

        return jobs
