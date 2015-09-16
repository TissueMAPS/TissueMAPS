import os
import yaml
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


class ClusterRoutines(object):

    '''
    Abstract base class for cluster routines.
    It provides a common framework for creation, submission and monitoring
    of jobs via `GC3Pie <https://code.google.com/p/gc3pie/>`_.
    '''

    __metaclass__ = ABCMeta

    def __init__(self, experiment, prog_name, logging_level='critical'):
        '''
        Initialize an instance of class ClusterRoutines.

        Parameters
        ----------
        experiment: Experiment
            experiment object
        prog_name: str
            name of the corresponding program (command line interface)
        logging_level: str, optional
            configuration of GC3Pie logger; either "debug", "info", "warning",
            "error" or "critical" (defaults to ``"critical"``)
        '''
        self.experiment = experiment
        self.prog_name = prog_name
        self.configure_logging(logging_level)

    @staticmethod
    def configure_logging(level):
        '''
        Configure logging for GC3Pie.

        Parameters
        ----------
        level: str
            logging level
        '''
        def map_logging_level(level):
            if level == 'debug':
                return logging.DEBUG
            elif level == 'info':
                return logging.INFO
            elif level == 'warning':
                return logging.WARNING
            elif level == 'error':
                return logging.ERROR
            elif level == 'critical':
                return logging.CRITICAL
        logger = logging.getLogger(__name__)
        # TODO: create logger for program
        gc3libs.configure_logger(level=map_logging_level(level))

    @cached_property
    def cycles(self):
        '''
        Returns
        -------
        List[Wellplate or Slide]
            cycle objects
        '''
        self._cycles = self.experiment.cycles
        return self._cycles

    @property
    def project_dir(self):
        '''
        Returns
        -------
        str
            directory where joblist file and log output will be stored
        '''
        self._project_dir = os.path.join(self.experiment.dir,
                                         'tm_%s' % self.prog_name)
        return self._project_dir

    @property
    def log_dir(self):
        '''
        Returns
        -------
        str
            directory where log files are stored
        '''
        self._log_dir = os.path.join(self.project_dir, 'log')
        return self._log_dir

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
            joblist element, i.e. description of a single job
        '''
        pass

    @abstractmethod
    def collect_job_output(self, joblist, **kwargs):
        '''
        Collect the output of jobs and fuse them if necessary.

        Parameters
        ----------
        joblist: List[dict]
            job descriptions
        **kwargs: dict
            additional variable input arguments as key-value pairs
        '''
        pass

    @abstractmethod
    def create_joblist(self, **kwargs):
        '''
        Create a list with information required for the creation and processing
        of individual jobs.

        There are two kinds of jobs:
        * *run* jobs: tasks that are processed in parallel
        * *collect* job: a single task that is processed after *run* jobs
          are terminated, i.e. successfully completed

        Each batch (element of the *run* joblist) must provide the following
        key-value pairs:
        * "id": one-based job indentifier number (*int*)
        * "inputs": absolute paths to input files required for the job
          (List[*str*] or Dict[*str*, List[*str*]])
        * "outputs": absolute paths to output files required for the job
          (List[*str*] or Dict[*str*, List[*str*]])

        In case a *collect* job is required, the corresponding batch must
        provide the following key-value pairs:
        * "inputs": absolute paths to input files required for the job
          (List[*str*] or Dict[*str*, List[*str*]])
        * "outputs": absolute paths to output files required for the job
          (List[*str*] or Dict[*str*, List[*str*]])

        A complete joblist has the following structure::

            {
                'run': [
                    {
                        'id': int
                        'inputs': list or dict
                        'outputs': list or dict
                    },
                    ...
                    ]
                'collect':
                    {
                        'inputs': list or dict
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
    def apply_statistics(self, joblist, wells, sites, channels, output_dir,
                         **kwargs):
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
        '''
        pass

    @property
    def joblist_file(self):
        '''
        Returns
        -------
        str
            absolute path to the joblist file
        '''
        self._joblist_file = os.path.join(self.project_dir,
                                          '%s.jobs' % self.prog_name)
        return self._joblist_file

    def read_joblist(self):
        '''
        Read joblist from YAML file.

        Returns
        -------
        List[dict]
            job descriptions

        Raises
        ------
        OSError
            when `joblist_file` does not exist
        '''
        if not os.path.exists(self.joblist_file):
            raise OSError('Joblist file does not exist: %s'
                          % self.joblist_file)
        with open(self.joblist_file, 'r') as f:
            joblist = yaml.load(f.read())
        # TODO: check structure of joblist
        return joblist

    def write_joblist(self, joblist):
        '''
        Write joblist to file as YAML.

        Parameters
        ----------
        joblist: List[dict]
            job descriptions

        Note
        ----
        Create log directory if it does not exist.
        '''
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)
        # TODO: check structure of joblist
        with open(self.joblist_file, 'w') as f:
            f.write(yaml.dump(joblist, default_flow_style=False))

    def print_joblist(self, joblist):
        '''
        Print joblist to standard output in YAML format.
        '''
        print yaml.safe_dump(joblist, default_flow_style=False)

    def submit_jobs(self, jobs):
        '''
        Create a GC3Pie engine that submits jobs to a cluster or cloud
        for parallel and/or sequential processing and monitors their progress.

        Parameters
        ----------
        jobs: gc3libs.workflow.DependentTaskCollection
            GC3Pie task collection of "jobs" that should be processed

        Returns
        -------
        bool
            indicating whether processing of jobs was successful
        '''
        # Create an `Engine` instance for running jobs in parallel
        e = gc3libs.create_engine()
        # Put all output files in the same directory
        e.retrieve_overwrites = True
        # Add tasks to engine instance
        e.add(jobs)

        # Periodically check the status of submitted jobs
        while jobs.execution.state != gc3libs.Run.State.TERMINATED:
            print '\n%s' % self.create_timestamp()
            print '"%s": %s ' % (jobs.jobname, jobs.execution.state)
            # `progess` will do the GC3Pie magic:
            # submit new jobs, update status of submitted jobs, get
            # results of terminating jobs etc...
            e.progress()

            for task in jobs.iter_tasks():
                if task.jobname == jobs.jobname:
                    continue
                print '"%s": %s ' % (task.jobname, task.execution.state)

            terminated_count = 0
            total_count = 0
            for task in jobs.iter_workflow():
                if task.jobname == jobs.jobname:
                    continue
                if task.execution.state == gc3libs.Run.State.TERMINATED:
                    terminated_count += 1
                total_count += 1
            print 'terminated: %d of %d jobs' % (terminated_count, total_count)
            time.sleep(5)

        success = True
        for task in jobs.iter_workflow():
            if(task.execution.returncode != 0
                    or task.execution.exitcode != 0):
                print 'job "%s" failed.' % task.jobname
                success = False

        return success

    def create_jobs(self, joblist, shared_network=True, virtualenv='tmaps'):
        '''
        Create a GC3Pie task collection of "jobs".

        Parameters
        ----------
        joblist: Dict[List[dict]]
            job descriptions
        shared_network: bool, optional
            whether worker nodes have access to a shared network
            or filesystem (defaults to ``True``)
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
        be treated the same way and easily be combined into larger workflows.
        '''
        run_jobs = ParallelTaskCollection(
                        jobname='%s_run_jobs' % self.prog_name)
        for i, batch in enumerate(joblist['run']):

            jobname = '%s_run_job-%.5d' % (self.prog_name, batch['id'])
            timestamp = self.create_datetimestamp()
            log_out_file = '%s_%s.out' % (jobname, timestamp)
            log_err_file = '%s_%s.err' % (jobname, timestamp)

            if shared_network:
                inputs = []
                outputs = []
            else:
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

        if 'collect' in joblist.keys():

            batch = joblist['collect']

            jobname = '%s_collect_job' % self.prog_name
            timestamp = self.create_datetimestamp()
            log_out_file = '%s_%s.out' % (jobname, timestamp)
            log_err_file = '%s_%s.err' % (jobname, timestamp)

            if shared_network:
                inputs = []
                outputs = []
            else:
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

            jobs = SequentialTaskCollection(
                        tasks=[run_jobs, collect_job],
                        jobname='%s_workflow' % self.prog_name)

        else:

            jobs = SequentialTaskCollection(
                        tasks=[run_jobs],
                        jobname='%s_workflow' % self.prog_name)

        return jobs
