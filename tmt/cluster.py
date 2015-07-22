import os
import yaml
import time
import datetime
import re
import socket
import gc3libs
import subprocess32

import logging
logger = logging.getLogger(__name__)
# gc3libs.configure_logger(level=logging.DEBUG)
gc3libs.configure_logger(level=logging.CRITICAL)


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


def write_joblist(filename, joblist):
    '''
    Write joblist to YAML file.

    Parameters
    ----------
    filename: str
        name of the YAML file
    joblist: List[dict]
        job descriptions
    '''
    with open(filename, 'w') as joblist_file:
            joblist_file.write(yaml.dump(joblist, default_flow_style=False))


def read_joblist(filename):
    '''
    Read joblist to YAML file.

    Parameters
    ----------
    filename: str
        name of the YAML file

    Returns
    -------
    List[dict]
        job descriptions

    Raises
    ------
    OSError
        when `filename` does not exist
    '''
    if not os.path.exists(filename):
        raise OSError('Joblist file does not exist: %s' % filename)
    with open(filename, 'r') as joblist_file:
            return yaml.load(joblist_file.read())


def submit_jobs_gc3pie(jobs):
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
        print '%s: Status of jobs "%s": %s ' % (create_timestamp(),
                                                jobs.jobname,
                                                jobs.execution.state)
        # `progess` will do the GC3Pie magic:
        # submit new jobs, update status of submitted jobs, get
        # results of terminating jobs etc...
        e.progress()
        for task in jobs.iter_workflow():
            if task.jobname == jobs.jobname:
                continue
            print '%s: Status of job "%s": %s ' % (create_timestamp(),
                                                   task.jobname,
                                                   task.execution.state)
        time.sleep(3)

    for task in jobs.iter_workflow():
        if(task.execution.returncode != 0
                or task.execution.exitcode != 0):
            print 'Job "%s" failed.' % task.jobname
            # TODO: resubmit

    print '%s: Jobs "%s" terminated.' % (create_timestamp(), jobs.jobname)


class Cluster(object):
    '''
    Class for cluster job handling.
    '''

    def __init__(self, output_dir):
        '''
        Initialize Cluster class.
        
        Parameters
        ----------
        output_dir: str
            path to directory were output log files should be saved
        '''
        self._on_brutus = None
        self.output_dir = output_dir

    @property
    def on_brutus(self):
        '''
        Are we on Brutus?

        Returns
        -------
        bool
        '''
        if self._on_brutus is None:
            hostname = socket.gethostname()
            if re.search(r'brutus', hostname):
                self._on_brutus = True
            else:
                self._on_brutus = False
        return self._on_brutus

    def submit(self, command):
        '''
        Submit a standard 8h job. Runs locally if not on the cluster.

        Parameters
        ----------
        command: List[str]
            elements of the bash command, e.g. ['find', '-name', 'bla*']
        '''
        if self.on_brutus:
            bsub = [
                 'bsub', '-W', '8:00', '-o', self.output_dir,
                 '-R', 'rusage[mem=4000,scratch=4000]'
            ]
            subprocess32.call(bsub + command)
        else:
            subprocess32.call(command)
