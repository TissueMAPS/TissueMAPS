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


class Cluster(object):

    '''
    Abstract base class for APIs of subpackages, i.e. individual command line
    interfaces for the different TissueMAPS routines.
    It provides a common framework for creation, submission and monitoring
    of jobs via `GC3Pie <https://code.google.com/p/gc3pie/>`_.
    '''

    __metaclass__ = ABCMeta

    def __init__(self, logging_level='critical'):
        '''
        Initialize an instance of class Cluster.

        Parameters
        ----------
        logging_level: str, optional
            configuration of GC3Pie logger; either "debug" or "critical"
            (defaults to ``"critical"``)
        '''
        self.configure_logging(logging_level)

    @staticmethod
    def configure_logging(level):
        '''
        Configure logging for GC3Pie.

        Parameters
        ----------
        level: str
            logging level; either "debug" or "critical"
        '''
        def map_logging_level(level):
            if level == 'debug':
                return logging.DEBUG
            elif level == 'critical':
                return logging.CRITICAL
        gc3libs.configure_logger(level=map_logging_level(level))

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
    def create_batches(li, n):
        '''
        Break a list into several n-sized partitions, i.e. batches.

        Parameters
        ----------
        li: list
        n: int
            batch size, i.e. number of elements per batch

        Returns
        -------
        List[list]
            batches
        '''
        n = max(1, n)
        return [li[i:i + n] for i in range(0, len(li), n)]

    @abstractproperty
    def name(self):
        '''
        Returns
        -------
        str
            name of the program in lower case letters
        '''
        pass

    @abstractproperty
    def log_dir(self):
        '''
        Returns
        -------
        str
            path to the directory where log files should be stored
        '''
        pass

    @abstractmethod
    def build_command(self, batch=None):
        '''
        Build a command for GC3Pie submission. For further information on
        the structure of the command see
        `subprocess <https://docs.python.org/2/library/subprocess.html>`_.

        Parameter
        ---------
        batch: Dict[str, int or List[str]], optional
            id and specification of input/output of the job that should be
            processed

        Returns
        -------
        List[str]
            substrings of the command call
        '''
        pass

    @abstractmethod
    def create_joblist(self, batch_size):
        '''
        Create a list of information required for the creation and processing
        of individual jobs.

        Parameters
        ----------
        batch_size: int
            number of files that should be processed together as one job

        Returns
        -------
        List[Dict[str, int or List[str]]
            information for each job

        Note
        ----
        Must specify "id" (one-based job indentifier number), "inputs"
        (absolute paths to input files) and "outputs" (relative paths to output
        files, relative to *log_dir*!) for each job.
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
        self._joblist_file = os.path.join(self.experiment,
                                          '%s.jobs' % self.name)
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

    def write_joblist(self):
        '''
        Write joblist to file as YAML.
        '''
        with open(self.joblist_file, 'w') as f:
            f.write(yaml.dump(self.joblist, default_flow_style=False))

    def submit(self, jobs):
        '''
        Create a GC3Pie engine that submits jobs to a cluster or cloud
        for parallel processing and monitors their progress.

        Parameters
        ----------
        jobs: gc3libs.workflow.ParallelTaskCollection[gc3libs.Application]
            collection of "jobs" that should be processed in parallel
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
            time.sleep(3)

        for task in jobs.iter_workflow():
            if(task.execution.returncode != 0
                    or task.execution.exitcode != 0):
                print 'Job "%s" failed.' % task.jobname
            # TODO: resubmit

        print '%s: Jobs "%s" terminated.' % (self.create_timestamp(),
                                             jobs.jobname)

    def create_jobs(self, joblist, shared_network=True, virtual_env='tmaps'):
        '''
        Create a GC3Pie parallel task collection of "jobs".

        Parameters
        ----------
        joblist: List[Dict[str, int or List[str]]]
            id and specification of input/output of each job
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
        jobs = ParallelTaskCollection(jobname='%s_jobs' % self.name)

        for i, batch in enumerate(joblist):

            jobname = '%s_job-%.5d' % (self.name, batch['id'])
            timestamp = self.create_datetimestamp()
            log_out_file = '%s_%s.out' % (jobname, timestamp)
            log_err_file = '%s_%s.err' % (jobname, timestamp)

            if shared_network:
                inputs = []
                outputs = []
            else:
                # If no shared network is available, files need to be copied.
                # They are temporary stored in ~/.gc3pie_jobs.
                inputs = batch['inputs']
                outputs = [os.path.relpath(f, self.log_dir)
                           for f in batch['outputs']]

            # Add individual task to collection
            app = gc3libs.Application(
                    arguments=self.build_command(batch),
                    inputs=inputs,
                    outputs=outputs,
                    output_dir=self.log_dir,
                    jobname=jobname,
                    # write STDOUT and STDERR combined into a single log file
                    stdout=log_out_file,
                    stderr=log_err_file,
                    # activate the virtual environment
                    application_name=virtual_env
            )
            jobs.add(app)
        return jobs
