import os
import yaml
import time
import datetime
from abc import ABCMeta
from abc import abstractmethod
from abc import abstractproperty
import gc3libs
from gc3libs.workflow import ParallelTaskCollection
import logging
from . import utils


class ClusterRoutine(object):

    '''
    Abstract base class for cluster routines of command line interfaces.
    It provides a common framework for creation, submission and monitoring
    of jobs via `GC3Pie <https://code.google.com/p/gc3pie/>`_.
    '''

    __metaclass__ = ABCMeta

    def __init__(self, prog_name, logging_level='critical'):
        '''
        Initialize an instance of class ClusterRoutine.

        Parameters
        ----------
        prog_name: str
            name of the corresponding program (command line interface)
        logging_level: str, optional
            configuration of GC3Pie logger; either "debug", "info", "warning",
            "error" or "critical" (defaults to ``"critical"``)
        '''
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
        gc3libs.configure_logger(level=map_logging_level(level))

    @abstractproperty
    def log_dir(self):
        '''
        Returns
        -------
        str
            directory where log files should be stored
        '''
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
    def _build_command(self, batch):
        # Build a command for GC3Pie submission. For further information on
        # the structure of the command see documentation of subprocess package:
        # https://docs.python.org/2/library/subprocess.html.
        pass

    @abstractmethod
    def create_joblist(self, **kwargs):
        '''
        Create a list of information required for the creation and processing
        of individual jobs.

        Each batch (element of the joblist) must provide the following
        key-value pairs:
        * "id": one-based job indentifier number (*int*)
        * "inputs": absolute paths to input files required for the job
          (List[*str*] or Dict[*str*, List[*str*]])
        * "outputs": absolute paths to output files required for the job
          (List[*str*] or Dict[*str*, List[*str*]])

        Parameters
        ----------
        **kwargs: dict
            additional variable input arguments as key-value pairs

        Returns
        -------
        List[dict]
            job descriptions

        Note
        ----
        In case there is no shared network available to worker nodes,
        *inputs* are copied to and *outputs* back from the remote cluster.
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
        self._joblist_file = os.path.join(self.log_dir,
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
            return yaml.load(f.read())

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
            os.mkdir(self.log_dir)
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
        for parallel processing and monitors their progress.

        Parameters
        ----------
        jobs: gc3libs.workflow.ParallelTaskCollection[gc3libs.Application]
            collection of "jobs" that should be processed in parallel

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
            print '%s: Status of jobs "%s": %s ' % (self.create_timestamp(),
                                                    jobs.jobname,
                                                    jobs.execution.state)
            # `progess` will do the GC3Pie magic:
            # submit new jobs, update status of submitted jobs, get
            # results of terminating jobs etc...
            e.progress()
            for task in jobs.iter_workflow():
                if task.jobname == jobs.jobname:
                    continue
                print '%s: Status of job "%s": %s ' % (self.create_timestamp(),
                                                       task.jobname,
                                                       task.execution.state)
            time.sleep(10)

        success = True
        for task in jobs.iter_workflow():
            if(task.execution.returncode != 0
                    or task.execution.exitcode != 0):
                print 'Job "%s" failed.' % task.jobname
                success = False
            # TODO: resubmit

        print '%s: Jobs "%s" terminated.' % (self.create_timestamp(),
                                             jobs.jobname)

        return success

    def create_jobs(self, joblist, shared_network=True, virtual_env='tmaps'):
        '''
        Create a GC3Pie parallel task collection of "jobs".

        Parameters
        ----------
        joblist: List[dict]
            job descriptions
        shared_network: bool, optional
            whether worker nodes have access to a shared network
            or filesystem (defaults to ``True``)
        virtual_env: str, optional
            name of a virtual environment that should be activated
            (defaults to ``"tmaps"``)

        Warning
        -------
        There is a bug in GDC3Pie that prevents the use of relative paths for
        the *stdout* and *stderr* arguments of `gc3libs.Application` in order
        to bundle log files in a subdirectory of the *output_dir*. To avoid
        the accumulation of log files in the same folder as the output files,
        we use the `log_dir` as *output_dir* and make the path of output
        files relative to it.

        Returns
        -------
        gc3libs.workflow.ParallelTaskCollection
            jobs
        '''
        jobs = ParallelTaskCollection(jobname='%s_jobs' % self.prog_name)

        for i, batch in enumerate(joblist):

            jobname = '%s_job-%.5d' % (self.prog_name, batch['id'])
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
                elif isinstance(batch['inputs'], list):
                    inputs = batch['inputs']
                else:
                    raise TypeError('The value of the key "inputs" of the '
                                    'elements in the joblist '
                                    'must be of type dict or list.')
                if isinstance(batch['outputs'], dict):
                    outputs = utils.flatten(batch['outputs'].values())
                elif isinstance(batch['outputs'], list):
                    outputs = batch['inputs']
                else:
                    raise TypeError('The value of the key "outputs" of the '
                                    'elements in the joblist '
                                    'must be of type dict or list.')
                outputs = [os.path.relpath(f, self.log_dir) for f in outputs]

            # Add individual task to collection
            app = gc3libs.Application(
                    arguments=self._build_command(batch),
                    inputs=inputs,
                    outputs=outputs,
                    output_dir=self.log_dir,
                    jobname=jobname,
                    stdout=log_out_file,
                    stderr=log_err_file,
                    # activate the virtual environment
                    application_name=virtual_env
            )
            jobs.add(app)
        return jobs

    # TODO: add job for "collect"
