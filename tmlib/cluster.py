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
from gc3libs.workflow import ParallelTaskCollection
from gc3libs.workflow import SequentialTaskCollection
import logging
from . import utils
from . import text_readers
from . import text_writers

logger = logging.getLogger(__name__)

class BasicClusterRoutines(object):

    __metaclass__ = ABCMeta

    def __init__(self, experiment):
        '''
        Initialize an instance of class ClusterRoutines.

        Parameters
        ----------
        experiment: Experiment
            configured experiment object
        '''
        self.experiment = experiment

    @cached_property
    def cycles(self):
        '''
        Returns
        -------
        List[Wellplate or Slide]
            configured cycle objects
        '''
        self._cycles = self.experiment.cycles
        return self._cycles

    @abstractproperty
    def project_dir(self):
        pass

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
        return datetime.datetime.fromtimestamp(t).strftime('%Y-%m-%d_%H:%M:%S')

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
        return datetime.datetime.fromtimestamp(t).strftime('%H:%M:%S')

    @staticmethod
    def _create_batches(li, n):
        # Create a list of lists from a list, where each sublist has length n
        n = max(1, n)
        return [li[i:i + n] for i in range(0, len(li), n)]

    def submit_jobs(self, jobs, monitoring_interval):
        '''
        Create a GC3Pie engine that submits jobs to a cluster
        for parallel and/or sequential processing and monitors their progress.

        Parameters
        ----------
        jobs: gc3libs.workflow.SequentialTaskCollection
            GC3Pie task collection of "jobs" that should be submitted
        monitoring_interval: int
            monitoring interval in seconds

        Returns
        -------
        bool
            indicating whether processing of jobs was successful
        '''
        logger.debug('monitoring interval: %ds' % monitoring_interval)
        # Create an `Engine` instance for running jobs in parallel
        e = gc3libs.create_engine()
        # Put all output files in the same directory
        e.retrieve_overwrites = True
        # Add tasks to engine instance
        e.add(jobs)

        # Periodically check the status of submitted jobs
        while jobs.execution.state != gc3libs.Run.State.TERMINATED:
            logger.info('"%s": %s ' % (jobs.jobname, jobs.execution.state))
            # `progess` will do the GC3Pie magic:
            # submit new jobs, update status of submitted jobs, get
            # results of terminating jobs etc...
            e.progress()

            for task in jobs.iter_tasks():
                if task.jobname == jobs.jobname:
                    continue
                logger.info('"%s": %s ' % (task.jobname, task.execution.state))

            terminated_count = 0
            total_count = 0
            for task in jobs.iter_workflow():
                if task.jobname == jobs.jobname:
                    continue
                if task.execution.state == gc3libs.Run.State.TERMINATED:
                    terminated_count += 1
                total_count += 1
            logger.info('terminated: %d of %d jobs'
                        % (terminated_count, total_count))
            time.sleep(monitoring_interval)

        success = True
        for task in jobs.iter_workflow():
            if(task.execution.returncode != 0
                    or task.execution.exitcode != 0):
                logger.error('job "%s" failed.' % task.jobname)
                success = False

        return success

    def kill_jobs(self, jobs):
        '''
        Kill all currently active jobs and set their status to "terminated".

        Parameters
        ----------
        jobs: gc3libs.workflow.SequentialTaskCollection
            GC3Pie task collection of "jobs" that should be killed
        '''
        logger.info('killing jobs')
        jobs.kill()

    @abstractmethod
    def create_jobs(self, job_descriptions, no_shared_network=False,
                    virtualenv='tmaps'):
        pass


class ClusterRoutines(BasicClusterRoutines):

    '''
    Abstract base class for cluster routines.
    It provides a common framework for creation, submission and monitoring
    of jobs via `GC3Pie <https://code.google.com/p/gc3pie/>`_.
    '''

    __metaclass__ = ABCMeta

    def __init__(self, experiment, prog_name):
        '''
        Initialize an instance of class ClusterRoutines.

        Parameters
        ----------
        experiment: Experiment
            configured experiment object
        prog_name: str
            name of the corresponding program (command line interface)
        '''
        super(ClusterRoutines, self).__init__(experiment)
        self.experiment = experiment
        self.prog_name = prog_name

    @cached_property
    def project_dir(self):
        '''
        Returns
        -------
        str
            directory where *.job* files and log output will be stored
        '''
        self._project_dir = os.path.join(self.experiment.dir,
                                         'tmaps_%s' % self.prog_name)
        if not os.path.exists(self._project_dir):
            logger.debug('create project directory: %s' % self._project_dir)
            os.mkdir(self._project_dir)
        return self._project_dir

    @cached_property
    def log_dir(self):
        '''
        Returns
        -------
        str
            directory where log files are stored
        '''
        self._log_dir = os.path.join(self.project_dir, 'log')
        if not os.path.exists(self._log_dir):
            logger.debug('create directory for log files: %s' % self._log_dir)
            os.mkdir(self._log_dir)
        return self._log_dir

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
        Get job descriptions from individual *.job* files and combine them into
        the format required by the `build_jobs()` method.

        Returns
        -------
        dict
            job descriptions
        '''
        directory = self.job_descriptions_dir
        job_descriptions = dict()
        job_descriptions['run'] = list()
        run_job_files = glob.glob(os.path.join(directory, '*_run_*.job'))
        if not run_job_files:
            logger.debug('No run job descriptor files found')
        collect_job_files = glob.glob(os.path.join(directory, '*_collect.job'))
        if not collect_job_files:
            logger.debug('No collect job descriptor file found')
        for f in run_job_files:
            batch = text_readers.read_json(f)
            job_descriptions['run'].append(batch)
        if collect_job_files:
            job_descriptions['collect'] = text_readers.read_json(collect_job_files[0])
        return job_descriptions

    def list_output_files(self, job_descriptions):
        '''
        Provide a list of all output files that should be created by the
        program.

        Parameters
        ----------
        job_descriptions: List[dict]
            job descriptions

        See also
        --------
        `get_job_descriptions_from_files`_
        '''
        files = list()
        if job_descriptions['run']:
            run_files = utils.flatten([
                j['outputs'].values() for j in job_descriptions['run']
            ])
            if all([isinstance(f, list) for f in run_files]):
                files.extend(utils.flatten(run_files))
            else:
                files.extend(run_files)
        if 'collect' in job_descriptions.keys():
            files.extend(
                utils.flatten(job_descriptions['collect']['outputs'].values())
            )
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
        '''
        filename = os.path.join(self.job_descriptions_dir,
                                '%s_run_%.5d.job' % (self.prog_name, job_id))
        return filename

    def build_collect_job_filename(self):
        '''
        Returns
        -------
        str
            absolute path to the file that holds the description of the
            job with the given `job_id`
        '''
        filename = os.path.join(self.job_descriptions_dir,
                                '%s_collect.job' % self.prog_name)
        return filename

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
            when file does not exist
        '''
        batch = text_readers.read_json(filename)
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
        Creates log directory if it does not exist and adds the job filename
        to "inputs" (required in case no shared network is available).

        See also
        --------
        `get_job_descriptions_from_files`_
        '''
        if not os.path.exists(self.job_descriptions_dir):
            os.makedirs(self.job_descriptions_dir)
        for batch in job_descriptions['run']:
            job_file = self.build_run_job_filename(batch['id'])
            batch['inputs']['job_file'] = job_file
            text_writers.write_json(job_file, batch)
        if 'collect' in job_descriptions.keys():
            job_file = self.build_collect_job_filename()
            job_descriptions['collect']['inputs']['job_file'] = job_file
            text_writers.write_json(job_file, job_descriptions['collect'])

    def _build_run_command(self, batch):
        # Build a command for GC3Pie submission. For further information on
        # the structure of the command see documentation of subprocess package:
        # https://docs.python.org/2/library/subprocess.html.
        job_id = batch['id']
        command = [self.prog_name]
        command.append(self.experiment.dir)
        command.extend(['run', '--job', str(job_id)])
        return command

    def _build_collect_command(self):
        command = [self.prog_name]
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
            job_descriptions element, i.e. description of a single job
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
    def create_job_descriptions(self, **kwargs):
        '''
        Create job descriptions with information required for the creation and
        processing of individual jobs.

        There are two kinds of jobs:
        * *run* jobs: tasks that are processed in parallel
        * *collect* job: a single task that is processed after *run* jobs
          are terminated, i.e. successfully completed

        Each batch (element of the *run* job_descriptions) must provide the following
        key-value pairs:
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

        A complete job_descriptions has the following structure::

            {
                'run': [
                    {
                        'id': int,
                        'inputs': list or dict,
                        'outputs': list or dict,
                    },
                    ...
                    ]
                'collect':
                    {
                        'inputs': list or dict,
                        'outputs': list or dict
                    }
            }

        Parameters
        ----------
        **kwargs: dict
            additional variable input arguments as key-value pairs

        Returns
        -------
        Dict[str, List[dict] or dict]
            job descriptions
        '''
        pass

    @abstractmethod
    def apply_statistics(self, job_descriptions, wells, sites, channels,
                         output_dir, **kwargs):
        '''
        Apply the calculated statistics to images.

        Parameters
        ----------
        wells: List[str]
            well identifiers of images that should be processed
        sites: List[int]
            one-based site indices of images that should be processed
        channels: List[str]
            channel names of images that should be processed
        output_dir: str
            absolute path to directory where the processed images should be
            stored
        **kwargs: dict
            additional variable input arguments as key-value pairs:
            * "illumcorr": correct for illumination artifacts (*bool*)

        See also
        --------
        `get_job_descriptions_from_files`_
        '''
        pass

    def print_job_descriptions(self, job_descriptions):
        '''
        Print `job_descriptions` to standard output in YAML format.

        Parameters
        ----------
        job_descriptions: Dict[List[dict]]
            description of inputs and outputs or individual jobs

        See also
        --------
        `get_job_descriptions_from_files`_
        '''
        print yaml.safe_dump(job_descriptions, default_flow_style=False)

    def create_jobs(self, job_descriptions, no_shared_network=False,
                    virtualenv='tmaps'):
        '''
        Create a GC3Pie task collection of "jobs".

        Parameters
        ----------
        job_descriptions: Dict[List[dict]]
            description of inputs and outputs or individual jobs
        no_shared_network: bool, optional
            whether worker nodes have access to a shared network
            or filesystem (defaults to ``False``)
        virtualenv: str, optional
            name of a virtual environment that should be activated
            (defaults to ``"tmaps"``)

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

        See also
        --------
        `get_job_descriptions_from_files`_
        '''
        run_jobs = ParallelTaskCollection(
                        jobname='tmaps_%s_run' % self.prog_name)

        logging.debug('create run jobs: ParallelTaskCollection')
        for i, batch in enumerate(job_descriptions['run']):

            jobname = 'tmaps_%s_run_%.5d' % (self.prog_name, batch['id'])
            timestamp = self.create_datetimestamp()
            log_out_file = '%s_%s.out' % (jobname, timestamp)
            log_err_file = '%s_%s.err' % (jobname, timestamp)

            if no_shared_network:
                logging.warning('no shared network: files are copied')
                # If no shared network is available, files need to be copied.
                # They are temporary stored in ~/.gc3pie_jobs.
                if isinstance(batch['inputs'].values()[0], list):
                    inputs = utils.flatten(batch['inputs'].values())
                else:
                    inputs = batch['inputs'].values()

                if isinstance(batch['outputs'].values()[0], list):
                    outputs = utils.flatten(batch['outputs'].values())
                else:
                    outputs = batch['outputs'].values()
                outputs = [os.path.relpath(f, self.log_dir) for f in outputs]
            else:
                inputs = list()
                outputs = list()

            # Add individual task to collection
            job = gc3libs.Application(
                    arguments=self._build_run_command(batch),
                    inputs=inputs,
                    outputs=outputs,
                    output_dir=self.log_dir,
                    jobname=jobname,
                    stdout=log_out_file,
                    stderr=log_err_file,
                    # activate the virtual environment
                    application_name=virtualenv
            )
            run_jobs.add(job)

        if 'collect' in job_descriptions.keys():
            logging.debug('create collect job: Application')

            batch = job_descriptions['collect']

            jobname = '%s_collect' % self.prog_name
            timestamp = self.create_datetimestamp()
            log_out_file = '%s_%s.out' % (jobname, timestamp)
            log_err_file = '%s_%s.err' % (jobname, timestamp)

            if no_shared_network:
                # If no shared network is available, files need to be copied.
                # They are temporary stored in ~/.gc3pie_jobs.
                if isinstance(batch['inputs'], dict):
                    inputs = utils.flatten(batch['inputs'].values())
                else:
                    inputs = batch['inputs']

                if isinstance(batch['outputs'], dict):
                    outputs = utils.flatten(batch['outputs'].values())
                else:
                    outputs = batch['inputs']
                outputs = [os.path.relpath(f, self.log_dir) for f in outputs]
            else:
                inputs = list()
                outputs = list()

            collect_job = gc3libs.Application(
                    arguments=self._build_collect_command(),
                    inputs=inputs,
                    outputs=outputs,
                    output_dir=self.log_dir,
                    jobname=jobname,
                    stdout=log_out_file,
                    stderr=log_err_file,
                    # activate the virtual environment
                    application_name=virtualenv
            )

            logging.debug('add run & collect jobs to SequentialTaskCollection')
            jobs = SequentialTaskCollection(
                        tasks=[run_jobs, collect_job],
                        jobname='tmaps_%s' % self.prog_name)

        else:

            logging.debug('add run jobs to SequentialTaskCollection')
            jobs = SequentialTaskCollection(
                        tasks=[run_jobs],
                        jobname='tmaps_%s' % self.prog_name)

        return jobs
