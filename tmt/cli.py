# encoding: utf-8
import os
import sys
import traceback
import shutil
import argparse
from abc import ABCMeta
from abc import abstractproperty
from abc import abstractmethod
from . import cfg
from . import utils


def command_line_call(parser):
    '''
    Call a command line interface.

    Parameters
    ----------
    parser: argparse.ArgumentParser
        argument parser object
    '''
    args = parser.parse_args()

    try:
        if args.handler:
            args.handler(args)
            print '🍺  Done!'
        else:
            parser.print_help()
    except Exception as error:
        sys.stdout.write('😞  Failed!\n')
        print 'Error message: "%s"\n' % str(error)
        for tb in traceback.format_tb(sys.exc_info()[2]):
            print tb


class CommandLineInterface(object):

    '''
    Abstract base class for command line interfaces.
    '''

    __metaclass__ = ABCMeta

    def __init__(self, args):
        '''
        Initialize an instance of class CommandLineInterface.

        Parameters
        ----------
        args: argparse.Namespace
            parsed command line arguments

        Note
        ----
        Default configuration settings are overwritten in case a custom
        configuration file is provided by the command line interface.
        '''
        self.args = args
        self.print_logo()
        if self.args.cfg_file:
            print 'Using configuration file: %s' % self.args.cfg_file
            self.args.cfg = self.read_cfg_file(self.args.cfg_file)
        else:
            self.args.cfg = cfg

    @property
    def default_cfg_file(self):
        '''
        Returns
        -------
        str
            absolute path to the default configuration file

        See also
        --------
        `tmt.cfg`_
        '''
        self._default_cfg_file = os.path.join(os.path.dirname(__file__),
                                              'tmt.cfg')
        return self._default_cfg_file

    @abstractproperty
    def api_instance(self):
        '''
        Initialize an instance of the API class corresponding to the specific
        command line interface with the required command line arguments.

        See also
        --------
        `tmt.cluster`_
        '''
        pass

    @abstractmethod
    def call(args):
        '''
        Handler function that can be called by an argparse subparser.
        Initializes an instance of the class and calls the method corresponding
        to the specified subparser with the parsed command line arguments.

        Parameters
        ----------
        args: argparse.Namespace
            parsed command line arguments

        Note
        ----
        `args` must contain the attribute "subparser", which specifies the name
        of the subparser. The names of the subparsers have to match names of
        methods.
        '''
        pass

    @abstractmethod
    def print_logo():
        pass

    @staticmethod
    def read_cfg_file(filename):
        '''
        Read configuration settings from YAML file.

        Parameters
        ----------
        filename: str
            absolute path to the configuration file
        '''
        return utils.read_yaml(filename)

    def joblist(self):
        '''
        Process arguments of "joblist" subparser.

        Parameters
        ----------
        args: argparse.Namespace
            parsed command line arguments
        '''
        print 'JOBLIST'
        api = self.api_instance
        print '.  create joblist'
        joblist = api.create_joblist(self.args.batch_size)
        print '.  write joblist to file: %s' % api.joblist_file
        api.write_joblist(joblist)
        print '.  joblist:'
        api.print_joblist(joblist)

    def run(self):
        '''
        Process arguments of "run" subparser.

        Parameters
        ----------
        args: argparse.Namespace
            parsed command line arguments
        '''
        print 'RUN'
        api = self.api_instance
        print '.  read joblist'
        joblist = api.read_joblist()
        print '.  run job'
        batch = joblist[self.args.job-1]
        api.run(batch, self.args.cfg_file)

    def submit(self):
        '''
        Process arguments of "submit" subparser.

        Parameters
        ----------
        args: argparse.Namespace
            parsed command line arguments
        '''
        print 'SUBMIT'
        api = self.api_instance
        if os.path.exists(api.log_dir):
            if not os.path.basename(api.log_dir).startswith('log_'):
                raise ValueError('Log directory incorrectly specified.')
            print '.  overwrite output of previous submission'
            if self.args.overwrite:
                shutil.rmtree(api.log_dir)
            else:
                shutil.move(api.log_dir, '{name}_{time}'.format(
                                            name=api.log_dir,
                                            time=api.create_datetimestamp))
        print '.  read joblist'
        joblist = api.read_joblist()
        print '.  create jobs'
        jobs = api.create_jobs(joblist)
        print '.  submit jobs'
        api.submit(jobs)
