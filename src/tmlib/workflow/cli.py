import os
import sys
import traceback
import logging
import shutil
import yaml
import argparse
import socket
from cached_property import cached_property
from abc import ABCMeta
from abc import abstractproperty
from abc import abstractmethod

from tmlib import __version__
from tmlib.workflow.args import InitArgs
from tmlib.workflow.args import SubmitArgs
from tmlib.workflow.args import ResubmitArgs
from tmlib.workflow.args import RunArgs
from tmlib.workflow.args import CollectArgs
from tmlib.workflow.args import CleanupArgs
from tmlib.workflow.args import LogArgs
from tmlib.workflow.args import InfoArgs
from tmlib.workflow.args import GeneralArgs
from tmlib.workflow import load_method_args
from tmlib.workflow import load_var_method_args
from tmlib.logging_utils import configure_logging
from tmlib.logging_utils import map_logging_verbosity

logger = logging.getLogger(__name__)

AVAILABLE_METHODS = {
    'init', 'submit', 'resume', 'resubmit', 'run', 'collect',
    'cleanup', 'log', 'info'
}


def create_method_args(step_name, method_name, **kwargs):
    '''Creates the argument object required as an input argument for methods of
    the :py:class:`tmlib.cli.CommandLineInterface` class.

    Parameters
    ----------
    step_name: str
        name of the step (command line program)
    method_name: str
        name of the method for which arguments should be build
    **kwargs: dict, optional
        description of keyword arguments that are passed to the method

    Returns
    -------
    tmlib.workflow.args.GeneralArgs
        arguments object that can be parsed to the specified method

    Note
    ----
    The function knows which arguments to strip from `kwargs`.

    See also
    --------
    :py:func:`tmlib.workflow.load_method_args`
    :py:func:`tmlib.workflow.load_var_method_args`
    :py:class:`tmlibtmlib.workflow.args.Args`
    '''
    args_handler = load_method_args(method_name)
    method_args = args_handler(**kwargs)
    variable_args_handler = load_var_method_args(step_name, method_name)
    if variable_args_handler is not None:
        method_args.variable_args = variable_args_handler(**kwargs)
    return method_args


class CommandLineInterface(object):

    '''Abstract base class for command line interfaces.

    Note
    ----
    There must be a method for each subparser, where the name of the method
    has to match that of the subparser.
    '''

    __metaclass__ = ABCMeta

    def __init__(self, api_instance, verbosity):
        '''
        Parameters
        ----------
        api_instance: tmlib.api.ClusterRoutines
            instance of API class to which processing is delegated
        verbosity: int
            logging level

        See also
        --------
        :py:func:`tmlib.logging_utils.map_logging_verbosity`
        '''
        self.api_instance = api_instance
        self.verbosity = verbosity

    @property
    def name(self):
        '''str: name of the step (command line program)'''
        return self.__class__.__name__.lower()

    @staticmethod
    def main(parser):
        '''Main entry point for command line interfaces.

        Parsers the command line arguments to the corresponding handler,
        retrieves the specified experiment from the database, and
        configures logging.

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

        # Silence some chatty loggers
        gc3libs_logger = logging.getLogger('gc3.gc3libs')
        gc3libs_logger.setLevel(logging.CRITICAL)
        apscheduler_logger = logging.getLogger('apscheduler')
        apscheduler_logger.setLevel(logging.CRITICAL)

        try:
            arguments.call(name=parser.prog, args=arguments)
            logger.info('COMPLETED')
            sys.exit(0)
            return 0
        except Exception as error:
            sys.stderr.write('\nFAILED:\n%s\n' % str(error))
            exc_type, exc_value, exc_traceback = sys.exc_info()
            for tb in traceback.format_tb(exc_traceback):
                sys.stderr.write(tb)
            sys.exit(1)
            return 1

    @abstractmethod
    def call(name, args):
        '''Executes the command line call.

        Initializes an instance of the step-specific implementation of the
        :py:class:`tmlib.workflow.cli.CommandLineInterface` abstract base class
        and calls the method matching the name of the specified subparser
        with the parsed arguments.

        Parameters
        ----------
        name: str
            name of the step (the command line program)
        args: argparse.Namespace
            parsed command line arguments
        '''
        pass

    def _call(self, args):
        logger.debug(
            'call "%s" method of class "%s" with the parsed arguments',
            args.method_name, self.__class__.__name__
        )
        method_args = create_method_args(step_name=self.name, **vars(args))
        getattr(self, args.method_name)(method_args)

    @abstractmethod
    def _print_logo():
        '''Prints the step-specific logo to standard output (console).'''
        pass

    def cleanup(self, args):
        '''Processes arguments provided by the "cleanup" subparser, which
        removes all output files or directories from a previous submission.

        Parameters
        ----------
        args: tmlibtmlib.workflow.args.CleanupArgs
            method-specific arguments
        '''
        self._print_logo()
        self.api_instance.delete_previous_job_output()

    def init(self, args):
        '''Processes arguments provided by the "init" subparser, which creates
        the job descriptor files required for submission.

        Parameters
        ----------
        args: tmlibtmlib.workflow.args.InitArgs
            method-specific arguments

        Returns
        -------
        dict
            batches
        '''
        self._print_logo()
        api = self.api_instance
        logger.info('delete previous job output')
        if not args.keep_output:
            api.delete_previous_job_output()
        logger.debug(
            'remove log reports and batches of previous submission'
        )
        shutil.rmtree(api.batches_location)
        os.mkdir(api.batches_location)

        logger.info('create batches')
        batches = api.create_batches(args.variable_args)
        if not batches['run']:
            raise ValueError('No batches were created.')
        logger.info('write batches to files')
        api.write_batch_files(batches)
        return batches

    def run(self, args):
        '''Processes arguments provided by the "run" subparser, which runs
        an individual job on the local computer.

        Parameters
        ----------
        args: tmlibtmlib.workflow.args.RunArgs
            method-specific arguments
        '''
        self._print_logo()
        api = self.api_instance
        logger.info('read job description from batch file')
        batch_file = api.build_batch_filename_for_run_job(args.job)
        batch = api.read_batch_file(batch_file)
        logger.info('run job #%d' % batch['id'])
        api.run_job(batch)

    def info(self, args):
        '''Processes arguments provided by the "info" subparser, which prints
        the description of an individual job to the console.

        Parameters
        ----------
        args: tmlibtmlib.workflow.args.LogArgs
            method-specific arguments
        '''
        if args.job is not None and args.phase != 'run':
            raise AttributeError(
                'Argument "job" can only be set when '
                'value of argument "phase" is "run".'
            )
        if args.job is None and args.phase == 'run':
            raise AttributeError(
                'Argument "job" is required '
                'when "phase" is set to "run".'
            )
        api = self.api_instance
        if args.phase == 'run':
            batch_file = api.build_batch_filename_for_run_job(args.job)
        else:
            batch_file = api.build_batch_filename_for_collect_job()
        batch = api.read_batch_file(batch_file)
        print('\nJOB DESCRIPTION\n===============\n\n%s'
              % yaml.safe_dump(batch, default_flow_style=False))

    def log(self, args):
        '''Processes arguments provided by the "log" subparser, which prints
        the log output of an individual job to the console.

        Parameters
        ----------
        args: tmlibtmlib.workflow.args.LogArgs
            method-specific arguments
        '''
        if args.job is not None and args.phase != 'run':
            raise AttributeError(
                'Argument "job" can only be set when '
                'value of argument "phase" is "run".'
            )
        if args.job is None and args.phase == 'run':
            raise AttributeError(
                'Argument "job" is required '
                'when "phase" is set to "run".'
            )
        api = self.api_instance
        log = api.get_log_output_from_files(args.job)
        print('\nOUTPUT\n======\n\n%s\n\nERROR\n=====\n\n%s'
              % (log['stdout'], log['stderr']))

    @cached_property
    def batches(self):
        '''dict: job descriptions'''
        api = self.api_instance
        logger.debug('read batches from files')
        return api.get_batches_from_files()

    @property
    def expected_outputs(self):
        '''List[str]: absolute paths to outputs that should be generated by
        the step
        '''
        api = self.api_instance
        logger.debug('get expected outputs from batches')
        return api.list_output_files(self.batches)

    @property
    def required_inputs(self):
        '''List[str]: absolute paths to inputs that are required by the step'''
        api = self.api_instance
        logger.debug('get required inputs from batches')
        return api.list_input_files(self.batches)

    def create_jobs(self, duration, memory, cores, phase=None, ids=None):
        '''Creates *jobs* based on previously created batches.
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
        api = self.api_instance
        logger.debug('allocated time: %s', duration)
        logger.debug('allocated memory: %d GB', memory)
        logger.debug('allocated cores: %d', cores)
        if phase == 'run':
            if ids is not None:
                logger.info('create run jobs %s', ', '.join(map(str, ids)))
                batches = dict()
                batches['run'] = [
                    j for j in self.batches['run'] if j['id'] in ids
                ]
            else:
                batches = dict()
                batches['run'] = self.batches['run']
        elif phase == 'collect':
            logger.info('create collect job')
            if 'collect' not in self.batches.keys():
                raise ValueError(
                    'Step "%s" doesn\'t have a "collect" phase.'
                    % self.name
                )
            batches = dict()
            batches['collect'] = self.batches['collect']
        else:
            logger.info('create all jobs')
            batches = self.batches
        step = api.create_step()
        return api.create_jobs(
            step=step,
            batches=batches,
            duration=duration,
            memory=memory,
            cores=cores
        )

    def submit(self, args):
        '''Processes arguments provided by the "submit" subparser, which
        submits jobs to the cluster and monitors their status.

        Parameters
        ----------
        args: tmlibtmlib.workflow.args.SubmitArgs
            method-specific arguments
        '''
        self._print_logo()
        api = self.api_instance
        if args.jobs is not None and args.phase != 'run':
            raise AttributeError(
                'Argument "job" is required when "phase" is set to "run".'
            )
        jobs = self.create_jobs(
            duration=args.duration,
            memory=args.memory,
            cores=args.cores,
            phase=args.phase,
            ids=args.jobs
        )
        session = api.create_gc3pie_session()
        logger.debug('add jobs to session "%s"', session.name)
        session.add(jobs)
        session.save_all()
        logger.debug('add session to engine store')
        engine = api.create_gc3pie_engine()
        engine._store = session.store
        logger.info('submit and monitor jobs')
        try:
            api.submit_jobs(jobs, engine, args.interval, args.depth)
        except KeyboardInterrupt:
            logger.info('processing interrupted')
            logger.info('killing jobs')
            while True:
                engine.kill(jobs)
                engine.progress()
                if jobs.is_terminated:
                    break
        except Exception:
            raise

    def resubmit(self, args):
        '''Processes arguments provided by the "resubmit" subparser,
        which resubmits previously created jobs to the cluster and monitors
        their status.

        Parameters
        ----------
        args: tmlibtmlib.workflow.args.ResubmitArgs
            method-specific arguments

        Note
        ----
        Requires a prior call of :py:method:`tmlib.workflow.cli.submit`.
        '''
        # TODO: session has some delay, immediate resubmission may cause trouble
        self._print_logo()
        api = self.api_instance
        session = api.create_gc3pie_session()
        logger.debug('load jobs from session "%s"', session.name)
        job_ids = session.list_ids()
        jobs = session.load(int(job_ids[-1]))
        logger.debug('add session to engine store')
        engine = api.create_gc3pie_engine()
        engine._store = session.store
        logger.info('resubmit and monitor jobs')
        try:
            api.submit_jobs(jobs, engine, args.interval, args.depth)
        except KeyboardInterrupt:
            logger.info('processing interrupted')
            logger.info('killing jobs')
            while True:
                engine.kill(jobs)
                engine.progress()
                if jobs.is_terminated:
                    break
        except Exception:
            raise

    def collect(self, args):
        '''Processes arguments of the "collect" subparser, which collects the
        output of previously run jobs or performs a post-processing operation
        that cannot be parallelized. 

        Parameters
        ----------
        args: tmlibtmlib.workflow.args.CollectArgs
            method-specific arguments
        '''
        self._print_logo()
        api = self.api_instance
        logger.info('read job description from file')
        batch_file = api.build_batch_filename_for_collect_job()
        batch = api.read_batch_file(batch_file)
        logger.info('collect job output')
        api.collect_job_output(batch)

    @staticmethod
    def get_parser_and_subparsers(methods=None):
        '''Creates an argument parser object for a subclass of
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
        '''
        if methods is None:
            methods = AVAILABLE_METHODS
        # TODO: do this smarter, e.g. via pyCli, cement, or click package
        parser = argparse.ArgumentParser()
        parser.version == __version__
        GeneralArgs().add_to_argparser(parser)

        subparsers = parser.add_subparsers(
            dest='method_name', help='sub-commands')

        if 'init' in methods:
            init_parser = subparsers.add_parser(
                'init', help='initialize the program with required arguments')
            init_parser.description = '''
                Create a list of persistent batches for parallel
                processing, which are used to dynamically build GC3Pie jobs.
                The descriptions are stored on disk in form of JSON files.
                Note that in case of the existence of a previous submission,
                batches and log outputs will be overwritten
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
                processing and collect their outputs
            '''
            SubmitArgs().add_to_argparser(submit_parser)

        if 'resubmit' in methods:
            submit_parser = subparsers.add_parser(
                'resubmit',
                help='resubmit and monitor jobs')
            submit_parser.description = '''
                Create jobs, submit them to the cluster, monitor their
                processing and collect their outputs using an existing session.
            '''
            ResubmitArgs().add_to_argparser(submit_parser)

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
