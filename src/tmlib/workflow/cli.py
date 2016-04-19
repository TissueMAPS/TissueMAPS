import os
import sys
import traceback
import logging
import shutil
import yaml
import inspect
import socket
import argparse
import types
import importlib
import collections
from cached_property import cached_property
from abc import ABCMeta
from abc import abstractmethod
from abc import abstractproperty

from tmlib import __version__
from tmlib.workflow.registry import get_step_api
from tmlib.workflow.registry import get_step_args
from tmlib.workflow.registry import climethod
from tmlib.workflow.args import Argument
from tmlib.logging_utils import configure_logging
from tmlib.logging_utils import map_logging_verbosity
from tmlib.errors import WorkflowError

logger = logging.getLogger(__name__)


class CliMeta(ABCMeta):

    '''Metaclass that provides classes command line interface functionality.
    Generated classes behave as abstract base classes and need to be
    implemented for each workflow step. When the generated class has the
    attribute ``__abstract__`` set to ``True`` no command line functionality
    will be added to this class. Derived classes will, however, be automatically
    equipped with this functionality.

    This is achieved by adding an instance of :py:class:`argparse.ArgumentParser`
    to the derived class.
    The docstring of the class is used as value for the `description` attribute
    of the parser and a separate subparser is added for each method of the
    class that is decorated with :py:func:`tmlib.workflow.climethod`.
    The decorator provides descriptions for the arguments required, which are
    added to the corresponding subparser.
    The :py:method:`tmlib.workflow.cli.CommandLineInterface.init`
    and :py:method:`tmlib.workflow.cli.CommandLineInterace.submit` methods
    require additional step-specific arguments that are passed to the *API*
    methods :py:method:`tmlib.workflow.api.ClusterRoutines.create_batches` and
    :py:method:`tmlib.workflow.api.ClusterRoutines.create_jobs`, respectively.
    These arguments are handled separately, because they also need to be
    accessible outside the scope of the command line interace.
    They are provided by step-specific implementations of
    :py:class:`tmlib.workflow.args.BatchArguments` and
    :py:class:`tmlib.workflow.args.SubmissionArguments`, respectively,
    and are automatically loaded from the `args` module of the step package
    and added to corresponding subparser.
    '''

    def __init__(cls, clsname, bases, attrs):
        super(CliMeta, cls).__init__(clsname, bases, attrs)
        if '__abstract__' in vars(cls).keys():
            return
        pkg_name = '.'.join(cls.__module__.split('.')[:-1])
        pkg = importlib.import_module(pkg_name)
        cls.__doc__ = pkg.__description__
        cls.__logo__ = pkg.__logo__
        parser = argparse.ArgumentParser()
        parser.description = pkg.__description__
        parser.version = __version__
        # The parser for each step receives at least two arguments, which are
        # passed to the corresponding API class.
        parser.add_argument(
            'experiment_id', type=int,
            help='ID of the experiment that should be processed'
        )
        parser.add_argument(
            '--verbosity', '-v', action='count', default=0,
            help='increase logging verbosity'
        )
        # Extra arguments are added to the main parser as well because they
        # also need to be parssed to the constructor of the API class.
        step_name = cls.__name__.lower()
        BatchArgs, SubmissionArgs, ExtraArgs = get_step_args(step_name)
        if ExtraArgs is not None:
            for arg in ExtraArgs.iterargs():
                arg.add_to_argparser(parser)
        subparsers = parser.add_subparsers(dest='method', help='methods')
        subparsers.required = True
        flags = collections.defaultdict(list)
        for attr_name in dir(cls):
            if attr_name.startswith('__'):
                continue
            attr_value = getattr(cls, attr_name)
            # The climethod decorator provides argument descriptions via
            # the "args" attribute of the decoreated method.
            # These arguments are added to the method-specific subparser.
            if isinstance(attr_value, types.MethodType):
                if getattr(attr_value, 'is_climethod', None):
                    method_parser = subparsers.add_parser(
                        attr_name, help=attr_value.help
                    )
                    method_parser.description = attr_value.help
                    for arg in attr_value.args.iterargs():
                        arg.add_to_argparser(method_parser)
                        if arg.flag is not None:
                            flags[attr_name].append(arg.flag)
        # The "init" and "submit" methods require additional arguments
        # that also need to be accessible outside the scope of the
        # command line interface. Therefore, they are handled separately.
        # Each workflow step must implement BatchArguments and
        # SubmissionArguments and register them using the batch_args and
        # submission_args decorator, respectively.
        # These arguments are added to the corresponding method-specific
        # subparser as a separate group to highlight that they represent a
        # different type of argument.

        def add_step_specific_method_args(step_name, method_name, args_class):
            method_parser = subparsers.choices[method_name]
            parser_group = method_parser.add_argument_group(
                    'step-specific arguments'
            )
            for arg in args_class.iterargs():
                arg.add_to_argparser(parser_group)
                if arg.flag is not None:
                    flags[attr_name].append(arg.flag)

        add_step_specific_method_args(step_name, 'init', BatchArgs)
        setattr(cls, '_batch_args_class', BatchArgs)
        add_step_specific_method_args(step_name, 'submit', SubmissionArgs)
        setattr(cls, '_submission_args_class', SubmissionArgs)
        api = get_step_api(step_name)
        setattr(cls, '_api_class', api)
        setattr(cls, '_parser', parser)


class CommandLineInterface(object):

    '''Abstract base class for command line interfaces.

    Derived classes must implement abstract methods and properties
    and provide the attribute ``__cli__ = True`` to active command line
    interface functionality.
    '''

    __metaclass__ = CliMeta

    __abstract__ = True

    def __init__(self, api_instance):
        '''
        Parameters
        ----------
        api_instance: tmlib.api.ClusterRoutines
            instance of API class to which processing is delegated
        '''
        self.api_instance = api_instance

    @property
    def name(self):
        '''str: name of the step (command line program)'''
        return self.__class__.__name__.lower()

    @classmethod
    def main(cls):
        '''Main entry point for command line interfaces.

        Parses the command line arguments and configures logging.

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
        arguments = cls._parser.parse_args()

        configure_logging(logging.CRITICAL)
        logger = logging.getLogger('tmlib')
        level = map_logging_verbosity(arguments.verbosity)
        logger.setLevel(level)
        logger.debug('processing on node: %s', socket.gethostname())
        logger.debug('running program: %s' % cls._parser.prog)

        # Silence some chatty loggers
        gc3libs_logger = logging.getLogger('gc3.gc3libs')
        gc3libs_logger.setLevel(logging.CRITICAL)
        apscheduler_logger = logging.getLogger('apscheduler')
        apscheduler_logger.setLevel(logging.CRITICAL)

        try:
            logger.debug('instantiate API class "%s"', cls._api_class.__name__)
            # Derived CLI classes may provide additional arguments for the main
            # parser, i.e. arguments for the constructor of the API class.
            kwargs = dict()
            valid_arg_names = inspect.getargspec(cls._api_class.__init__).args
            for arg_name, arg_value in vars(arguments).iteritems():
                if arg_name in valid_arg_names:
                    kwargs[arg_name] = arg_value
            api_instance = cls._api_class(**kwargs)
            logger.debug('instantiate CLI class "%s"', cls.__name__)
            cli_instance = cls(api_instance)
            cli_instance(arguments)
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

    def __call__(self, cli_args):
        '''Executes the command line call.

        Calls the method matching the name of the specified subparser
        with the parsed arguments.

        Parameters
        ----------
        cli_args: argparse.Namespace
            parsed command line arguments
        '''
        logger.debug(
            'call "%s" method of CLI class "%s" with the parsed arguments',
            cli_args.method, self.__class__.__name__
        )
        # Strip the relevant arguments from the namespace
        method = getattr(self, cli_args.method)
        arg_names = inspect.getargspec(method).args[1:]
        arg_defaults = inspect.getargspec(method).defaults
        method_args = dict()
        for name in arg_names:
            logger.debug(
                'pass argument "%s" to method "%s" of class "%s"',
                name, cli_args.method, self.__class__.__name__
            )
            index = list(reversed(arg_names)).index(name)
            try:
                value = getattr(cli_args, name)
            except AttributeError:
                raise AttributeError(
                    'Argument "%s" was not parsed via command line' % name
                )
            if value is None:
                try:
                    value = arg_defaults[-index+1]
                    logger.debug(
                        'set value for argument "%s" for method "%s" '
                        'of class "%s" according to default value',
                        name, cli_args.method, self.__class__.__name__
                    )
                except:
                    pass
            method_args[name] = value
        if cli_args.method == 'init':
            self._batch_args = self._batch_args_class(**vars(cli_args))
        elif cli_args.method == 'submit':
            self._submission_args = self._submission_args_class(**vars(cli_args))
        method(**method_args)

    @classmethod
    def _print_logo(cls):
        '''Prints the step-specific logo to standard output (console).'''
        print cls.__logo__

    @climethod(
        help='''cleans up the output of a previous submission, i.e. removes
            files and database entries created by previously submitted jobs
        '''
    )
    def cleanup(self):
        self._print_logo()
        self.api_instance.delete_previous_job_output()

    @climethod(
        help='''creates batches for parallel processing and thereby
            defines how the computational task should be distrubuted over
            the cluster (also cleans up the output of previous submissions)
        '''
    )
    def init(self):
        self._print_logo()
        api = self.api_instance
        logger.info('delete previous job output')
        api.delete_previous_job_output()
        logger.debug('remove log reports and batches of previous submission')
        shutil.rmtree(api.batches_location)
        os.mkdir(api.batches_location)

        logger.info('create batches')
        batches = api.create_batches(self._batch_args)
        if not batches['run']:
            raise WorkflowError(
                'No batches were created!\n'
                'Did upstream workflow steps get submitted and did they '
                'complete successfully?'
            )
        logger.info('write batches to files')
        api.write_batch_files(batches)
        return batches

    @climethod(
        help='runs an invidiual jobs on the local machine',
        job_id=Argument(
            type=int, help='ID of the job that should be run', flag='j'
        )
    )
    def run(self, job_id):
        self._print_logo()
        api = self.api_instance
        logger.info('read job description from batch file')
        batch_file = api.build_batch_filename_for_run_job(job_id)
        batch = api.read_batch_file(batch_file)
        logger.info('run job #%d' % batch['id'])
        api.run_job(batch)

    @climethod(
        help='prints the description of a given batch job to the console',
        phase=Argument(
                type=str, default='run', choices={'run', 'collect'},
                help='phase of the workflow step to which the job belongs'
        ),
        job_id=Argument(
            type=int, flag='j',
            help='ID of the job for which information should be displayed'
        )
    )
    def info(self, phase, job_id):
        if job_id is not None and phase != 'run':
            raise AttributeError(
                'Argument "job_id" can only be set when '
                'value of argument "phase" is "run".'
            )
        if job_id is None and phase == 'run':
            raise AttributeError(
                'Argument "job_id" is required '
                'when "phase" is set to "run".'
            )
        api = self.api_instance
        if phase == 'run':
            batch_file = api.build_batch_filename_for_run_job(job_id)
        else:
            batch_file = api.build_batch_filename_for_collect_job()
        batch = api.read_batch_file(batch_file)
        print('\nJOB DESCRIPTION\n===============\n\n%s'
              % yaml.safe_dump(batch, default_flow_style=False))

    @climethod(
        help='prints the log output of a given batch job to the console',
        phase=Argument(
                type=str, default='run', choices={'run', 'collect'}, flag='p',
                help='phase of the workflow step to which the job belongs'
        ),
        job_id=Argument(
            type=int, help='ID of the job that should be run', flag='j'
        )
    )
    def log(self, phase, job_id):
        if job_id is not None and phase != 'run':
            raise AttributeError(
                'Argument "job_id" can only be set when '
                'value of argument "phase" is "run".'
            )
        if job_id is None and phase == 'run':
            raise AttributeError(
                'Argument "job_id" is required '
                'when "phase" is set to "run".'
            )
        api = self.api_instance
        log = api.get_log_output_from_files(job_id)
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

    def create_jobs(self, duration, memory, cores, phase=None, job_id=None):
        '''Creates *jobs* based on previously created batch descrptions.

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
        job_id: int, optional
            id of a single job that should be submitted (default: ``None``)

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
            if job_id is not None:
                logger.info('create run job %d', job_id)
                batches = dict()
                batches['run'] = [
                    j for j in self.batches['run'] if j['id'] == job_id 
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

    @climethod(
        help='''creates batch jobs, submits them to the cluster and
            monitors their status
        ''',
        phase=Argument(
            type=str, choices={'run', 'collect'}, flag='p',
            help='phase of the workflow step to which the job belongs'
        ),
        job_id=Argument(
            type=int, help='ID of the job that should be run', flag='j'
        ),
        monitoring_depth=Argument(
            type=int, help='number of child tasks that should be monitored',
            default=1, flag='m'
        )
    )
    def submit(self, phase, job_id, monitoring_depth):
        self._print_logo()
        api = self.api_instance
        if job_id is not None and phase != 'run':
            raise AttributeError(
                'Argument "job_id" is required when "phase" is set to "run".'
            )
        jobs = self.create_jobs(
            duration=self._submission_args.duration,
            memory=self._submission_args.memory,
            cores=self._submission_args.cores,
            phase=phase, job_id=job_id
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
            api.submit_jobs(jobs, engine, monitoring_depth=monitoring_depth)
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

    @climethod(
        help='''resubmits previously created jobs to the cluster and
            monitors their status
        ''',
        phase=Argument(
                type=str, choices={'run', 'collect'}, flag='p',
                help='phase of the workflow step to which the job belongs'
        ),
        job_id=Argument(
            type=int, help='ID of the job that should be run', flag='j'
        ),
        monitoring_depth=Argument(
            type=int, help='depth of monitoring the task hierarchy',
            default=1, flag='m'
        )
    )
    def resubmit(self, phase, job_id, monitoring_depth):
        # TODO: session has some delay, immediate resubmission may cause trouble
        self._print_logo()
        api = self.api_instance
        session = api.create_gc3pie_session()
        logger.debug('load jobs from session "%s"', session.name)
        task_ids = session.list_ids()
        task = session.load(int(task_ids[-1]))
        # Select an individual job based on "phase" and "job_id"
        if phase == 'run':
            job_index = 0
        elif phase == 'collect':
            if len(jobs.tasks) == 1:
                raise ValueError(
                    'Step "%s" doens\'t have a collect phase' % self.name
                )
            job_index = 1
        logger.debug('add session to engine store')
        engine = api.create_gc3pie_engine()
        engine._store = session.store
        logger.info('resubmit and monitor jobs')
        try:
            api.submit_jobs(
                jobs, engine, start_index=job_index,
                monitoring_depth=monitoring_depth
            )
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

    @climethod(
        help='''collects the output of run jobs, i.e. performs a
            post-processing operation that either cannot be parallelized
            or needs to be performed afterwards
        '''
    )
    def collect(self):
        self._print_logo()
        api = self.api_instance
        logger.info('read job description from file')
        batch_file = api.build_batch_filename_for_collect_job()
        batch = api.read_batch_file(batch_file)
        logger.info('collect job output')
        api.collect_job_output(batch)
