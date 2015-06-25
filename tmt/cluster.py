import re
import os
import yaml
from time import time
from datetime import datetime
import socket
import subprocess32


def create_batches(li, n):
    '''
    Separate a list into several n-sized sub-lists, i.e. batches.

    Parameters
    ----------
    li: list
        usually list of files
    n: int
        batch size

    Returns
    -------
    List[list]
        batches
    '''
    n = max(1, n)
    return [li[i:i + n] for i in range(0, len(li), n)]


def create_timestamp():
    '''
    Create timestamp in the form "year-month-day_hour_minute_second".
    Returns
    -------
    str
        timestamp
    '''
    return datetime.fromtimestamp(time()).strftime('%Y-%m-%d_%H-%M-%S')


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
