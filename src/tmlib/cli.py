import os
import sys
import traceback
import logging
import shutil
import json
import argparse
import socket
from cached_property import cached_property
from abc import ABCMeta
from abc import abstractproperty
from abc import abstractmethod
from . import __version__
from .args import InitArgs
from .args import SubmitArgs
from .args import RunArgs
from .args import CollectArgs
from .args import CleanupArgs
from .args import LogArgs
from .args import InfoArgs
from .tmaps.description import load_method_args
from .tmaps.description import load_var_method_args
from .logging_utils import configure_logging
from .logging_utils import map_logging_verbosity
from .errors import JobDescriptionError

logger = logging.getLogger(__name__)


def create_cli_method_args(prog_name, method_name, **kwargs):
    '''
    Create the argument object required as an input argument for methods of the
    :py:class:`tmlib.cli.CommandLineInterface` class.

    Parameters
    ----------
    prog_name: str
        name of the program
    method_name: str
        name of the method for which arguments should be build
    **kwargs: dict, optional
        mapping of key-value pairs with names and values of
        potential arguments

    Returns
    -------
    tmlib.args.GeneralArgs
        arguments object that can be parsed to the specified method

    Note
    ----
    The function knows which arguments to strip from `kwargs`.

    See also
    --------
    :py:func:`tmlib.tmaps.description.load_method_args`
    :py:func:`tmlib.tmaps.description.load_var_method_args`
    :py:class:`tmlib.args.Args`
    '''
    args_handler = load_method_args(method_name)
    method_args = args_handler(**kwargs)
    variable_args_handler = load_var_method_args(prog_name, method_name)
    if variable_args_handler is not None:
        method_args.variable_args = variable_args_handler(**kwargs)
    return method_args


def call_cli_method(cli_instance, method_name, method_args):
    '''
    Call a method of a *cli* class with the parsed command line arguments.

    Parameters
    ----------
    cli_instance: tmlib.cli.CommandLineInterface
        an instance of an implementation of the
        :py:class:`tmlib.cli.CommandLineInterface` base class
    method_name: str
        name of the method that should be called
    method_args: tmlib.args.GeneralArgs
        arguments required for the method

    See also
    --------
    :py:func:`tmlib.cli.build_cli_method_args`
    '''
    getattr(cli_instance, method_name)(method_args)


class CommandLineInterface(object):

    '''
    Abstract base class for command line interfaces.

    Note
    ----
    There must be a method for each subparser, where the name of the method
    has to match the name of the corresponding subparser.
    '''

    __metaclass__ = ABCMeta

    def __init__(self, experiment, verbosity):
        '''
        Initialize an instance of class CommandLineInterface.

        Parameters
        ----------
        experiment: tmlib.experiment.Experiment
            configured experiment object
        verbosity: int
            logging level

        See also
        --------
        :py:func:`tmlib.logging_utils.map_logging_verbosity`
        '''
        self.experiment = experiment
        self.verbosity = verbosity

    @staticmethod
    def main(parser):
        '''
        Main entry point for command line interface.

        Parsers the command line arguments to the corresponding handler
        and configures logging.

        Parameters
        ----------
        parser: argparse.ArgumentParser
            argument parser object

        Returns
        -------
        int
            ``0`` when program completes successfully and ``1`` otherwise

        Raises
        ------
        SystemExit
            exitcode ``1`` when the call raises an :py:class:`Exception`

        Warning
        -------
        Don't do any other logging configuration anywhere else!
        '''
        arguments = parser.parse_args()

        configure_logging(logging.CRITICAL)
        logger = logging.getLogger('tmlib')
        level = map_logging_verbosity(arguments.verbosity)
        logger.setLevel(level)
        logger.debug('processing on node: %s', socket.gethostname())
        logger.debug('running program: %s' % parser.prog)

        # Fine tune the output of some loggers
        gc3libs_logger = logging.getLogger('gc3.gc3libs')
        gc3libs_logger.setLevel(logging.CRITICAL)
        apscheduler_logger = logging.getLogger('apscheduler')
        apscheduler_logger.setLevel(logging.CRITICAL)
        vips_logger = logging.getLogger('gi.overrides.Vips')
        vips_logger.setLevel(logging.CRITICAL)

        try:
            if arguments.handler:
                arguments.handler(arguments)
            else:
                parser.print_help()
            logger.info('SUCCESSFULLY COMPLETED')
            sys.exit(0)
            return 0
        except Exception as error:
            sys.stderr.write('\nFAILED:\n%s\n' % str(error))
            for tb in traceback.format_tb(sys.exc_info()[2]):
                sys.stderr.write(tb)
            sys.exit(1)
            return 1

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
        '''
        Returns
        -------
        tmlib.api.ClusterRoutines
            an instance of a step-specific *api* class
        '''
        pass

    @abstractmethod
    def call(args):
        '''
        Handler function that can be called by a subparser.

        Initializes an instance of the class and calls the method matching the
        name of the specified subparser with the parsed arguments.

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
    def _print_logo():
        '''
        Prints the step-specific logo to standard output (console).
        '''
        pass

    def _cleanup(self):
        try:
            outputs = self.expected_outputs
            if outputs:
                logger.info('clean up output of previous submission')
                dont_exist_ix = [not os.path.exists(f) for f in outputs]
                if all(dont_exist_ix):
                    logger.debug('outputs don\'t exist')
                elif any(dont_exist_ix):
                    logger.warning('some outputs don\'t exist')
                for out in outputs:
                    if not os.path.exists(out):
                        logger.debug('output doesn\'t exist: %s', out)
                        continue
                    if os.path.isdir(out):
                        logger.debug('remove output directory: %s' % out)
                        shutil.rmtree(out)
                    else:
                        if out.endswith('data.h5'):
                            # Special case that is handled separately
                            logger.debug('keep data file: %s' % out)
                            continue
                        logger.debug('remove output file: %s' % out)
                        os.remove(out)
        except JobDescriptionError:
            # Expected outputs are retrieved from job descriptor files.
            # One ends up here in case no job descriptor files have been
            # created so far.
            logger.debug('nothing to clean up')

    def cleanup(self, args):
        '''
        Initialize an instance of the step-specific API class
        and process arguments provided by the "cleanup" subparser, which
        removes all output files or directories from a previous submission.

        Parameters
        ----------
        args: tmlib.args.CleanupArgs
            method-specific arguments
        '''
        self._print_logo()
        self._cleanup()

    def init(self, args):
        '''
        Initialize an instance of the step-specific API class
        and process arguments provided by the "init" subparser, which creates
        the job descriptor files required for submission.

        Parameters
        ----------
        args: tmlib.args.InitArgs
            method-specific arguments

        Returns
        -------
        dict
            job descriptions
        '''
        if not args.keep_output:
            self._cleanup()
        api = self._api_instance
        if args.backup:
            logger.info('backup log reports and job descriptions '
                        'of previous submission')
            timestamp = api.create_datetimestamp()
            shutil.move(api.log_dir,
                        '{name}_backup_{time}'.format(
                            name=api.log_dir,
                            time=timestamp))
            shutil.move(api.job_descriptions_dir,
                        '{name}_backup_{time}'.format(
                            name=api.job_descriptions_dir,
                            time=timestamp))
            if os.path.exists(api.session_dir):
                shutil.move(api.job_descriptions_dir,
                        '{name}_backup_{time}'.format(
                            name=api.session_dir,
                            time=timestamp))
        else:
            logger.debug('remove log reports and job descriptions '
                         'of previous submission')
            shutil.rmtree(api.job_descriptions_dir)
            shutil.rmtree(api.log_dir)

        logger.info('create job descriptions')
        job_descriptions = api.create_job_descriptions(args.variable_args)
        if not job_descriptions['run']:
            raise ValueError('No job descriptions were created.')
        logger.info('write job descriptions to files')
        api.write_job_files(job_descriptions)
        return job_descriptions

    def run(self, args):
        '''
        Initialize an instance of the step-specific API class
        and process arguments provided by the "run" subparser, which runs
        an individual job on the local computer.

        Parameters
        ----------
        args: tmlib.args.RunArgs
            method-specific arguments

        Note
        ----
        Requires calling :py:method:`tmlib.cli.init` first.
        '''
        self._print_logo()
        api = self._api_instance
        logger.info('read job description from file')
        job_file = api.build_run_job_filename(args.job)
        batch = api.read_job_file(job_file)
        logger.info('run job #%d' % batch['id'])
        api.run_job(batch)

    def info(self, args):
        '''
        Initialize an instance of the step-specific API class
        and process arguments provided by the "info" subparser, which prints
        the description of an individual job to the console.

        Parameters
        ----------
        args: tmlib.args.LogArgs
            method-specific arguments
        '''
        if args.job is not None and args.phase != 'run':
            raise AttributeError(
                    'Argument "job" can only be set when '
                    'value of argument "phase" is "run".')
        if args.job is None and args.phase == 'run':
            raise AttributeError(
                    'When "phase" is set to "run", '
                    'argument "job" has to be set as well.')
        api = self._api_instance
        if args.phase == 'run':
            job_file = api.build_run_job_filename(args.job)
        else:
            job_file = api.build_collect_job_filename()
        batch = api.read_job_file(job_file)
        print('\nDESCRIPTION\n===========\n\n%s'
              % json.dumps(
                    batch, sort_keys=True, indent=4, separators=(',', ': ')))

    def log(self, args):
        '''
        Initialize an instance of the step-specific API class
        and process arguments provided by the "log" subparser, which prints the
        log output of an individual job to the console.

        Parameters
        ----------
        args: tmlib.args.LogArgs
            method-specific arguments
        '''
        if args.job is not None and args.phase != 'run':
            raise AttributeError(
                    'Argument "job" can only be set when '
                    'value of argument "phase" is "run".')
        if args.job is None and args.phase == 'run':
            raise AttributeError(
                    'When "phase" is set to "run", '
                    'argument "job" has to be set as well.')
        api = self._api_instance
        log = api.get_log_output_from_files(args.job)
        print('\nOUTPUT\n======\n\n%s\n\nERROR\n=====\n\n%s'
              % (log['stdout'], log['stderr']))

    @cached_property
    def job_descriptions(self):
        '''
        Returns
        -------
        dict
            job descriptions retrieved from files
        '''
        api = self._api_instance
        logger.debug('read job descriptions from files')
        return api.get_job_descriptions_from_files()

    @property
    def expected_outputs(self):
        '''
        Read the job descriptions and extract the "outputs" information.

        Returns
        -------
        List[str]
            absolute paths to outputs that should be generated by the program
        '''
        api = self._api_instance
        logger.debug('get expected outputs from job descriptions')
        return api.list_output_files(self.job_descriptions)

    @property
    def required_inputs(self):
        '''
        Read the job descriptions and extract the "inputs" information.

        Returns
        -------
        List[str]
            absolute paths to inputs that are required by the program
        '''
        api = self._api_instance
        logger.debug('get required inputs from job descriptions')
        return api.list_input_files(self.job_descriptions)

    def create_jobs(self, duration, memory, cores, phase=None, ids=None):
        '''
        Create *jobs* based on previously created job descriptions.
        Job descriptions are loaded from files on disk and used to
        instantiate *job* objects. 

        Parameters
        ----------
        duration: str
            time allocated for a job in the format "HH:MM:SS"
        memory: int
            amount of memory allocated for a job in GB
        cores: int
            number of cores allocated for a job
        phase: str, optional
            phase for which jobs should be build; if not set jobs of *run* and
            *collect* phase will be submitted
            (options: ``"run"`` or ``"collect"``; default: ``None``)
        ids: List[int], optional
            ids of jobs that should be submitted (default: ``None``)

        Returns
        -------
        gc3libs.workflow.SequentialTaskCollection
            jobs

        See also
        --------
        :py:mod:`tmlib.jobs`
        '''
        api = self._api_instance
        logger.debug('allocated time: %s', duration)
        logger.debug('allocated memory: %d GB', memory)
        logger.debug('allocated cores: %d', cores)
        if phase == 'run':
            if ids is not None:
                logger.info('create run jobs %s', ', '.join(map(str, ids)))
                job_descriptions = dict()
                job_descriptions['run'] = [
                    j for j in self.job_descriptions['run'] if j['id'] in ids
                ]
            else:
                job_descriptions = dict()
                job_descriptions['run'] = self.job_descriptions['run']
        elif phase == 'collect':
            logger.info('create collect job')
            if 'collect' not in self.job_descriptions.keys():
                raise ValueError(
                            'Step "%s" doesn\'t have a "collect" phase.'
                            % self.name)
            job_descriptions = dict()
            job_descriptions['collect'] = self.job_descriptions['collect']
        else:
            logger.info('create all jobs')
            job_descriptions = self.job_descriptions
        jobs = api.create_jobs(
                job_descriptions=job_descriptions,
                duration=duration,
                memory=memory,
                cores=cores)
        return jobs

    def submit(self, args):
        '''
        Initialize an instance of the step-specific API class
        and process arguments provided by the "submit" subparser, which submits
        all jobs and monitors their status.

        Parameters
        ----------
        args: tmlib.args.SubmitArgs
            method-specific arguments

        Note
        ----
        Requires calling :py:method:`tmlib.cli.init` first.
        '''
        self._print_logo()
        api = self._api_instance
        if args.jobs is not None and args.phase != 'run':
            raise AttributeError(
                    'Argument "jobs" can only be set when '
                    'value of argument "phase" is "run".')
        if args.jobs is None and args.phase == 'run':
            raise AttributeError(
                    'When "phase" is set to "run", '
                    'argument "jobs" has to be set as well.')
        jobs = self.create_jobs(
                    duration=args.duration,
                    memory=args.memory,
                    cores=args.cores,
                    phase=args.phase,
                    ids=args.jobs)
        # TODO: check whether jobs were actually created
        if args.backup:
            session = api.create_session(backup=True)
        else:
            session = api.create_session()
        logger.debug('add jobs to session "%s"', api.session_dir)
        session.add(jobs)
        session.save_all()
        logger.info('submit and monitor jobs')
        api.submit_jobs(session,
                        monitoring_interval=args.interval,
                        monitoring_depth=args.depth)

    def collect(self, args):
        '''
        Initialize an instance of the step-specific API class
        and process arguments of the "collect" subparser, which collects the
        output of previously run jobs.

        Parameters
        ----------
        args: tmlib.args.CollectArgs
            method-specific arguments

        Note
        ----
        Requires calling :py:method:`tmlib.cli.init` and
        :py:method:`tmlib.cli.submit` first.
        '''
        self._print_logo()
        api = self._api_instance
        logger.info('read job description from file')
        job_file = api.build_collect_job_filename()
        batch = api.read_job_file(job_file)
        logger.info('collect job output')
        api.collect_job_output(batch)

    def _call(self, args):
        logger.debug('call "%s" method of class "%s"',
                     args.method_name, self.__class__.__name__)
        method_args = create_cli_method_args(prog_name=self.name, **vars(args))
        call_cli_method(self, args.method_name, method_args)

    @staticmethod
    def get_parser_and_subparsers(
            methods={'init', 'run', 'submit', 'collect', 'cleanup', 'log', 'info'}):
        '''
        Get an argument parser object for a subclass of
        :py:class:`tmlib.cli.CommandLineInterface` and a subparser object
        for each implemented method of the class.
        Subparsers may already have default arguments, but additional
        implementation specific arguments can be added.

        Parameters
        ----------
        methods: Set[str]
            methods for which a subparser should be returned (default: 
            ``{"init", "run", "submit", "collect", cleanup", "log", "info"}``)

        Returns
        -------
        Tuple[argparse.Argumentparser and argparse._SubParsersAction]
            parser and subparsers objects

        See also
        --------
        '''
        # TODO: do this smarter, e.g. via pyCli, cement, or click package
        parser = argparse.ArgumentParser()
        parser.version == __version__
        parser.add_argument(
            'experiment_dir', type=str, help='path to experiment directory')
        parser.add_argument(
            '-v', '--verbosity', dest='verbosity', action='count', default=0,
            help='increase logging verbosity to DEBUG (default: WARN)')
        parser.add_argument(
            '--version', action='version')

        subparsers = parser.add_subparsers(
            dest='method_name', help='sub-commands')

        if 'init' in methods:
            init_parser = subparsers.add_parser(
                'init', help='initialize the program with required arguments')
            init_parser.description = '''
                Create a list of persistent job descriptions for parallel
                processing, which are used to dynamically build GC3Pie jobs.
                The descriptions are stored on disk in form of JSON files.
                Note that in case of the existence of a previous submission,
                job descriptions and log outputs will be overwritten
                unless the "--backup" option is used.
                Also note that all outputs created by a previous submission
                will also be removed unless the "--keep_output" option is
                used.
            '''
            InitArgs().add_to_argparser(init_parser)
            # TODO: add step-specific args

        if 'run' in methods:
            run_parser = subparsers.add_parser(
                'run',
                help='run an individual job')
            run_parser.description = '''
                Run an individual job.
            '''
            RunArgs().add_to_argparser(run_parser)

        if 'submit' in methods:
            submit_parser = subparsers.add_parser(
                'submit',
                help='submit and monitor jobs')
            submit_parser.description = '''
                Create jobs, submit them to the cluster, monitor their
                processing and collect their outputs.
            '''
            SubmitArgs().add_to_argparser(submit_parser)

        if 'collect' in methods:
            collect_parser = subparsers.add_parser(
                'collect',
                help='collect job output after submission')
            collect_parser.description = '''
                Collect outputs of processed jobs and fuse them.
            '''
            CollectArgs().add_to_argparser(collect_parser)

        if 'cleanup' in methods:
            cleanup_parser = subparsers.add_parser(
                'cleanup',
                help='clean-up output of previous runs')
            cleanup_parser.description = '''
                Remove files and folders generated upon previous submissions.
            '''
            CleanupArgs().add_to_argparser(cleanup_parser)

        if 'log' in methods:
            log_parser = subparsers.add_parser(
                'log',
                help='show log message (standard output and error) of a job')
            log_parser.description = '''
                Print the log output of a job to the console.
            '''
            LogArgs().add_to_argparser(log_parser)

        if 'info' in methods:
            info_parser = subparsers.add_parser(
                'info',
                help='show description of a job')
            info_parser.description = '''
                Print the description (parameter settings, input, output)
                of a job to the console.
            '''
            InfoArgs().add_to_argparser(info_parser)

        return (parser, subparsers)
