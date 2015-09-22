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


def command_line_call(parser):
    '''
    Call a program via the command line.

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
        sys.stderr.write('Error message: "%s"\n' % str(error))
        for tb in traceback.format_tb(sys.exc_info()[2]):
            sys.stderr.write(tb)


class CommandLineInterface(object):

    '''
    Abstract base class for command line interfaces.

    Note
    ----
    There must be a method for each subparser, where the name of the method
    has to match the name of the corresponding subparser.
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
        configuration file is provided via the command line.
        '''
        self.args = args
        self.print_logo()

    @property
    def cfg(self):
        '''
        Returns
        -------
        Dict[str, str]
            configuration settings
        '''
        self._cfg = cfg
        return self._cfg

    @abstractproperty
    def name(self):
        '''
        Returns
        -------
        str
            name of the program
        '''
        pass

    @abstractproperty
    def _api_instance(self):
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
        `args` must have the attribute "subparser_name", which specifies the
        name of the subparser.
        '''
        pass

    @abstractmethod
    def print_logo():
        pass

    @property
    def _variable_init_args(self):
        # Since "init" requires more flexibility with respect to the number
        # of parsed arguments, we use a separate property, which can be
        # overwritten by subclasses to handle custom use cases
        kwargs = dict()
        return kwargs

    def init(self):
        '''
        Initialize an instance of the API class corresponding to the specific
        command line interface and process arguments of the "init" subparser.
        '''
        print 'JOBLIST'
        api = self._api_instance
        print '.  create joblist'
        kwargs = self._variable_init_args
        joblist = api.create_job_descriptions(**kwargs)
        if self.args.print_joblist:
            print '.  joblist:'
            api.print_joblist(joblist)
        else:
            # TODO: clean-up output of previous job
            if os.path.exists(api.log_dir):
                if self.args.backup:
                    print '.  create backup of previous submission'
                    shutil.move(api.log_dir, '{name}_backup_{time}'.format(
                                            name=api.log_dir,
                                            time=api.create_datetimestamp()))
                else:
                    print '.  overwrite output of previous submission'
                    shutil.rmtree(api.log_dir)
            print '.  write job descriptions to files'
            api.write_job_files(joblist)

    def run(self):
        '''
        Initialize an instance of the API class corresponding to the specific
        command line interface and process arguments of the "run" subparser.
        '''
        print 'RUN'
        api = self._api_instance
        print '.  read job description from file'
        job_file = api.build_run_job_filename(self.args.job)
        batch = api.read_job_file(job_file)
        print '.  run job'
        api.run_job(batch)

    def submit(self):
        '''
        Initialize an instance of the API class corresponding to the specific
        command line interface and process arguments of the "submit" subparser.
        '''
        print 'SUBMIT'
        api = self._api_instance
        print '.  read job descriptions from files'
        joblist = api.get_job_descriptions_from_files()
        print '.  create jobs'
        jobs = api.create_jobs(
                joblist=joblist,
                no_shared_network=self.args.no_shared_network,
                virtualenv=self.args.virtualenv)
        print '.  submit and monitor jobs'
        api.submit_jobs(jobs)

    @property
    def _variable_apply_args(self):
        kwargs = dict()
        return kwargs

    def apply(self):
        '''
        Initialize an instance of the API class corresponding to the specific
        command line interface and process arguments of the "apply" subparser.
        '''
        print 'APPLY'
        api = self._api_instance
        print '.  read job descriptions from files'
        joblist = api.get_job_descriptions_from_files()
        print '.  apply statistics'
        kwargs = self._variable_apply_args
        api.apply_statistics(
                joblist=joblist, wells=self.args.wells, sites=self.args.sites,
                channels=self.args.channels, output_dir=self.args.output_dir,
                **kwargs)

    def collect(self):
        '''
        Initialize an instance of the API class corresponding to the specific
        command line interface and process arguments of the "collect" subparser.
        '''
        print 'COLLECT'
        api = self._api_instance
        print '.  read job description from file'
        job_file = api.build_collect_job_filename()
        batch = api.read_job_file(job_file)
        print '.  collect job output'
        api.collect_job_output(batch)

    @staticmethod
    def get_parser_and_subparsers(
            required_subparsers=['init', 'run', 'submit']):
        '''
        Get an argument parser object and subparser objects with default
        arguments for use in command line interfaces.
        The subparsers objects can be extended with additional subparsers and
        additional arguments can be added to each individual subparser.

        Parameters
        ----------
        required_subparsers: List[str]
            subparsers that should be returned (defaults to
            ``["init", "run", "submit"]``)
        level: str
            level of the directory tree at which the command line interface
            operates; "cycle" when processing data at the level of an individual
            *cycle* folder or "experiment" when processing data at the level of
            the *experiment* folder, i.e. across multiple *cycle* folders

        Returns
        -------
        Tuple[argparse.Argumentparser and argparse._SubParsersAction]
            parser and subparsers objects
        '''
        parser = argparse.ArgumentParser()
        parser.add_argument(
            'experiment_dir', help='path to experiment directory')
        parser.add_argument(
            '-v', '--verbosity', action='count', default=0,
            help='increase logging verbosity, e.g. "-v" or -vvv"')
        parser.add_argument(
            '--version', action='version')

        if not required_subparsers:
            raise ValueError('At least one subparser has to specified')

        subparsers = parser.add_subparsers(dest='subparser_name',
                                           help='sub-commands')

        if 'init' in required_subparsers:
            init_parser = subparsers.add_parser(
                'init', help='initialize the program with required arguments')
            init_parser.description = '''
                Create a list of job descriptions (batches) for parallel
                processing and write it to a file in JSON format. Note that in
                case of existing previous submissions, the log output will be
                overwritten unless either the "--backup" or "--show" argument
                is specified.
            '''
            init_parser.add_argument(
                '--show', action='store_true', dest='print_joblist',
                help='print joblist to standard output '
                     'without writing it to file')
            init_parser.add_argument(
                '--backup', action='store_true',
                help='create a backup of the output of a previous submission')
            # NOTE: when additional arguments are provided, the property
            # `_variable_init_args` has to be overwritten

        if 'run' in required_subparsers:
            run_parser = subparsers.add_parser(
                'run',
                help='run an individual job')
            run_parser.description = '''
                Run an individual job.
            '''
            run_parser.add_argument(
                '-j', '--job', type=int, required=True,
                help='id of the job that should be processed')

        if 'submit' in required_subparsers:
            submit_parser = subparsers.add_parser(
                'submit',
                help='submit and monitor jobs')
            submit_parser.description = '''
                Create jobs, submit them to the cluster, monitor their
                processing and collect their outputs.
            '''
            submit_parser.add_argument(
                '--no_shared_network', dest='no_shared_network',
                action='store_true', help='when worker nodes don\'t have \
                access to a shared network; triggers copying of files')
            submit_parser.add_argument(
                '--virtualenv', type=str, default='tmaps',
                help='name of a virtual environment that should be activated '
                     '(default: tmaps')

        if 'collect' in required_subparsers:
            collect_parser = subparsers.add_parser(
                'collect',
                help='collect job output after submission')
            collect_parser.description = '''
                Collect outputs of processed jobs and fuse them.
            '''
            collect_parser.add_argument(
                '-o', '--output_dir', type=str,
                help='path to output directory')

        if 'apply' in required_subparsers:
            apply_parser = subparsers.add_parser(
                'apply',
                help='apply the calculated statistics')
            apply_parser.description = '''
                Apply the calculated statistics.
            '''
            apply_parser.add_argument(
                '-c', '--channels', nargs='+', type=str,
                help='names of channels to process')
            apply_parser.add_argument(
                '-s', '--sites',  nargs='+', type=int,
                help='numbers of sites to process')
            apply_parser.add_argument(
                '-w', '--wells', nargs='+', type=str,
                help='ids of wells to process')
            apply_parser.add_argument(
                '-a', '--all', action='store_true',
                help='when all images should be processed')
            apply_parser.add_argument(
                '-o', '--output_dir', type=str, required=True,
                help='path to output directory')

        return (parser, subparsers)
