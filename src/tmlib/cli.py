import os
import sys
import traceback
import logging
import shutil
import argparse
import gc3libs
from cached_property import cached_property
from abc import ABCMeta
from abc import abstractproperty
from abc import abstractmethod
from .args import InitArgs
from .args import SubmitArgs
from .args import RunArgs
from .args import CollectArgs
from .args import CleanupArgs
from .tmaps.description import load_method_args
from .tmaps.description import load_var_method_args
from .logging_utils import configure_logging
from .logging_utils import map_logging_verbosity
from .errors import JobDescriptionError

logger = logging.getLogger(__name__)


def command_line_call(parser):
    '''
    Main entry point for command line interfaces.

    Parsers the command line arguments to the corresponding handler
    and configures logging.

    Parameters
    ----------
    parser: argparse.ArgumentParser
        argument parser object

    Warning
    -------
    Don't do any other logging configuration anywhere else!
    '''
    arguments = parser.parse_args()

    configure_logging(logging.CRITICAL)
    logger = logging.getLogger('tmlib')
    level = map_logging_verbosity(arguments.verbosity)
    logger.setLevel(level)
    logger.debug('running program: %s' % parser.prog)

    # Fine tune the output of some loggers
    gc3libs_logger = logging.getLogger('gc3.gc3libs')
    gc3libs_logger.setLevel(logging.CRITICAL)

    apscheduler_logger = logging.getLogger('apscheduler')
    apscheduler_logger.setLevel(logging.CRITICAL)
    # configure_logger(apscheduler_logger, logging.CRITICAL)

    try:
        if arguments.handler:
            arguments.handler(arguments)
        else:
            parser.print_help()
    except Exception as error:
        sys.stderr.write('%s\n' % str(error))
        for tb in traceback.format_tb(sys.exc_info()[2]):
            sys.stderr.write(tb)
        sys.exit(1)


def build_cli_method_args_from_mapping(prog_name, method_name, **kwargs):
    '''
    Build the argument object required for a method of the
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
    :py:func:`tmlib.tmaps.workflow.load_method_args`
    :py:func:`tmlib.tmaps.workflow.load_var_method_args`
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
                        continue
                    if os.path.isdir(out):
                        logger.debug('remove output directory: %s' % out)
                        shutil.rmtree(out)
                    else:
                        logger.debug('remove output file: %s' % out)
                        os.remove(out)
        except JobDescriptionError:
            logger.debug('nothing to clean up')

    def cleanup(self, args):
        '''
        Initialize an instance of the API class corresponding to the program
        and process arguments provided by the "cleanup" subparser.

        Parameters
        ----------
        args: tmlib.args.CleanupArgs
            method-specific arguments
        '''
        self._print_logo()
        self._cleanup()

    def init(self, args):
        '''
        Initialize an instance of the API class corresponding to the program
        and process arguments provided by the "init" subparser.

        Parameters
        ----------
        args: tmlib.args.InitArgs
            method-specific arguments

        Returns
        -------
        dict
            job descriptions
        '''
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
        if args.display:
            api.print_job_descriptions(job_descriptions)
        else:
            logger.info('write job descriptions to files')
            api.write_job_files(job_descriptions)
        return job_descriptions

    def run(self, args):
        '''
        Initialize an instance of the API class corresponding to the program
        and process arguments provided by the "run" subparser.

        Parameters
        ----------
        args: tmlib.args.RunArgs
            method-specific arguments
        '''
        self._print_logo()
        api = self._api_instance
        logger.info('read job description from file')
        job_file = api.build_run_job_filename(args.job)
        batch = api.read_job_file(job_file)
        logger.info('run job #%d' % batch['id'])
        api.run_job(batch)

    @cached_property
    def _job_descriptions(self):
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
        return api.list_output_files(self._job_descriptions)

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
        return api.list_input_files(self._job_descriptions)

    def build_jobs(self, virtualenv, duration, memory):
        '''
        Build *jobs* based on prior created job descriptions.

        Parameters
        ----------
        virtualenv: str
            name of a Python virtual environment that needs to be activated
        duration: str
            time allocated for a job in HH:MM:SS
        memory: int
            memory allocated for a job in GB

        Returns
        -------
        gc3libs.workflow.SequentialTaskCollection
            jobs
        '''
        api = self._api_instance
        logger.info('create jobs')
        logger.info('allocated time: %s', duration)
        logger.info('allocated memory: %s', memory)
        jobs = api.create_jobs(
                job_descriptions=self._job_descriptions,
                virtualenv=virtualenv,
                duration=duration,
                memory=memory)
        return jobs

    def submit(self, args):
        '''
        Initialize an instance of the API class corresponding to the program
        and process arguments provided by the "submit" subparser.

        Parameters
        ----------
        args: tmlib.args.SubmitArgs
            method-specific arguments
        '''
        self._print_logo()
        api = self._api_instance
        jobs = self.build_jobs(
                    virtualenv=args.virtualenv,
                    duration=args.duration,
                    memory=args.memory)
        # TODO: check whether jobs were actually created
        # session = api.create_session(jobs)
        logger.info('submit and monitor jobs')
        api.submit_jobs(jobs,
                        monitoring_interval=args.interval,
                        monitoring_depth=args.depth)

    def collect(self, args):
        '''
        Initialize an instance of the API class corresponding to the program
        and process arguments of the "collect" subparser.

        Parameters
        ----------
        args: tmlib.args.CollectArgs
            method-specific arguments
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
        method_args = build_cli_method_args_from_mapping(
                            prog_name=self.name, **vars(args))
        call_cli_method(self, args.method_name, method_args)

    @staticmethod
    def get_parser_and_subparsers(
            required_subparsers=[
                'init', 'run', 'submit', 'collect', 'cleanup']):
        '''
        Get an argument parser object and subparser objects with default
        arguments for use in command line interfaces.
        The subparsers objects can be extended with additional subparsers and
        additional arguments can be added to each individual subparser.

        Parameters
        ----------
        required_subparsers: List[str]
            subparsers that should be returned (default: 
            ``["init", "run", "submit", "collect", cleanup"]``)

        Returns
        -------
        Tuple[argparse.Argumentparser and argparse._SubParsersAction]
            parser and subparsers objects

        Note
        ----
        In case an implementation of the base class doesn't use a particular
        subparser, the corresponding method must be overwritten such that it
        raises an AttributeError.
        '''
        parser = argparse.ArgumentParser()
        parser.add_argument(
            'experiment_dir', type=str, help='path to experiment directory')
        parser.add_argument(
            '-v', '--verbosity', dest='verbosity', action='count', default=0,
            help='increase logging verbosity to DEBUG (default: WARN)')
        parser.add_argument(
            '--version', action='version')

        if not required_subparsers:
            raise ValueError('At least one subparser has to be specified')

        subparsers = parser.add_subparsers(
            dest='method_name', help='sub-commands')

        if 'init' in required_subparsers:
            init_parser = subparsers.add_parser(
                'init', help='initialize the program with required arguments')
            init_parser.description = '''
                Create a list of persistent job descriptions for parallel
                processing, which are used to dynamically build GC3Pie jobs.
                The descriptions are stored on disk in form of JSON files.
                Note that in case of the existence of a previous submission,
                job descriptions and log outputs will be overwritten
                unless the "--backup" or "--display" argument is specified.
                All outputs created by a previous submission will also be
                removed!
            '''
            InitArgs().add_to_argparser(init_parser)

        if 'run' in required_subparsers:
            run_parser = subparsers.add_parser(
                'run', help='run an individual job')
            run_parser.description = '''
                Run an individual job.
            '''
            RunArgs().add_to_argparser(run_parser)

        if 'submit' in required_subparsers:
            submit_parser = subparsers.add_parser(
                'submit', help='submit and monitor jobs')
            submit_parser.description = '''
                Create jobs, submit them to the cluster, monitor their
                processing and collect their outputs.
            '''
            SubmitArgs().add_to_argparser(submit_parser)

        if 'collect' in required_subparsers:
            collect_parser = subparsers.add_parser(
                'collect', help='collect job output after submission')
            collect_parser.description = '''
                Collect outputs of processed jobs and fuse them.
            '''
            CollectArgs().add_to_argparser(collect_parser)

        if 'cleanup' in required_subparsers:
            cleanup_parser = subparsers.add_parser(
                'cleanup', help='clean-up output of previous runs')
            cleanup_parser.description = '''
                Remove files and folders generated upon previous submissions.
            '''
            CleanupArgs().add_to_argparser(cleanup_parser)

        return (parser, subparsers)
