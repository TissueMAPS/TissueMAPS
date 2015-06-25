import re
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
                 'bsub', '-W', '8:00', '-o', output_dir,
                 '-R', 'rusage[mem=4000,scratch=4000]'
            ]
            subprocess32.call(bsub + command)
        else:
            subprocess32.call(command)
