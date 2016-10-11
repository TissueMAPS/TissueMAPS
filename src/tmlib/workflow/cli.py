import os
import sys
import traceback
import logging
import shutil
import datetime
import yaml
import inspect
import socket
import argparse
import types
import time
import importlib
import collections
import gc3libs
from cached_property import cached_property
from abc import ABCMeta
from abc import abstractmethod
from abc import abstractproperty

from tmlib import __version__
from tmlib.workflow import get_step_api
from tmlib.workflow import get_step_args
from tmlib.workflow import climethod
from tmlib.workflow.args import Argument
from tmlib.workflow.utils import create_gc3pie_sql_store
from tmlib.workflow.utils import create_gc3pie_session
from tmlib.workflow.utils import create_gc3pie_engine
from tmlib.workflow.submission import SubmissionManager
from tmlib.workflow.description import WorkflowStepDescription
from tmlib.workflow.workflow import WorkflowStep
from tmlib.workflow.jobs import CliJobCollection
from tmlib.logging_utils import configure_logging
from tmlib.logging_utils import map_logging_verbosity
from tmlib.errors import WorkflowError
import tmlib.models as tm

logger = logging.getLogger(__name__)


class _CliMeta(ABCMeta):

    '''Metaclass that provides classes command line interface functionality.
    Generated classes behave as abstract base classes and need to be
    implemented for each workflow step. When the generated class has the
    attribute ``__abstract__`` set to ``True`` no command line functionality
    will be added to this class. Derived classes will, however, be automatically
    equipped with this functionality.

    '''

    def __init__(cls, clsname, bases, attrs):
        super(_CliMeta, cls).__init__(clsname, bases, attrs)
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
                if getattr(attr_value, 'is_climethod', False):
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

    def load_jobs(self):
        '''Loads previously submitted jobs from the database.

        Returns
        -------
        tmlib.workflow.job or tmlib.workflow.job.JobCollection
            loaded jobs
        '''
        with tm.utis.MainSession() as session:
            last_submission_id = session.query(func.max(tm.Submission.id)).\
                filter(
                    tm.Submission.experiment_id == self.api_instance.experiment_id,
                    tm.Submission.program == self.name
                ).\
                group_by(tm.Submission.experiment_id).\
                one()[0]
            last_submission = session.query(tm.Submission).\
                get(last_submission_id)
            job_id = last_submission.top_task_id
        store = create_gc3pie_sql_store()
        return store.load(job_id)


class CommandLineInterface(SubmissionManager):

    '''Abstract base class for command line interfaces.

    Each workflow step must implement this class. This will automatically
    provide derived classes with command line interface functionality
    in form of an instance of :class:`argparse.ArgumentParser`.
    The docstring of the derived class is also used for the `description`
    attribute of the parser for display in the command line.
    A separate subparser is added for each method of the derived class that is
    decorated with :func:`tmlib.workflow.climethod`. The decorator provides
    descriptions of the method arguments, which are also added to the
    corresponding subparser.

    The :method:`tmlib.workflow.cli.CommandLineInterface.init`
    and :method:`tmlib.workflow.cli.CommandLineInterace.submit` methods
    require additional step-specific arguments that are passed to the *API*
    methods :method:`tmlib.workflow.api.ClusterRoutines.create_batches` and
    :method:`tmlib.workflow.api.ClusterRoutines.create_run_jobs`,
    respectively. These arguments are handled separately, since they also need
    to be accessible outside the scope of the command line interace.
    They are provided by step-specific implementations of
    :class:`tmlib.workflow.args.BatchArguments` and
    :class:`tmlib.workflow.args.SubmissionArguments` and added to the
    corresponding `init` and `submit` subparsers, respectively.
    '''

    __metaclass__ = _CliMeta

    __abstract__ = True

    def __init__(self, api_instance):
        '''
        Parameters
        ----------
        api_instance: tmlib.api.ClusterRoutines
            instance of API class to which processing is delegated
        '''
        self.api_instance = api_instance
        super(CommandLineInterface, self).__init__(
            api_instance.experiment_id, self.name
        )

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
            exitcode ``1`` when the call raises an :class:`Exception`

        Warning
        -------
        Don't do any other logging configuration anywhere else!
        '''
        # NOTE: This hack is required to ensure correct UTF8 encoding.
        import sys
        reload(sys)
        sys.setdefaultencoding('utf-8')
        arguments = cls._parser.parse_args()

        configure_logging()
        logger = logging.getLogger('tmlib')
        level = map_logging_verbosity(arguments.verbosity)
        logger.setLevel(level)
        logger.debug('processing on node: %s', socket.gethostname())
        logger.debug('running program: %s' % cls.__name__.lower())

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

        logger.info('create batches for "run" and "collect" jobs')
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
            type=str, choices={'init', 'run', 'collect'}, flag='p',
            required=True,
            help='phase of the workflow step to which the job belongs'
        ),
        job_id=Argument(
            type=int, flag='j',
            help='ID of the job for which log output should be shown'
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
        log = api.get_log_output_from_files(phase, job_id)
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
        logger.debug('get expected outputs from batches')
        return self.api_instance.list_output_files(self.batches)

    @property
    def required_inputs(self):
        '''List[str]: absolute paths to inputs that are required by the step'''
        logger.debug('get required inputs from batches')
        return self.api_instance.list_input_files(self.batches)

    @climethod(
        help='''creates batch jobs for the "run" and "collect" phases, submits
            them to the cluster and monitors their status upon processing
            (requires a prior "init")
        ''',
        monitoring_depth=Argument(
            type=int, help='number of child tasks that should be monitored',
            default=1, flag='d'
        ),
        monitoring_interval=Argument(
            type=int, help='seconds to wait between monitoring iterations',
            default=10, flag='i'
        )
    )
    def submit(self, monitoring_depth, monitoring_interval):
        self._print_logo()
        submission_id, user_name = self.register_submission()
        api = self.api_instance

        jobs = CliJobCollection(api.step_name, submission_id)
        run_job_collection = api.create_run_job_collection(submission_id)
        run_jobs = api.create_run_jobs(
            submission_id, user_name, run_job_collection, self.batches['run'],
            duration=self._submission_args.duration,
            memory=self._submission_args.memory,
            cores=self._submission_args.cores
        )
        jobs.add(run_jobs)
        if api.has_collect_phase:
            collect_job = api.create_collect_job(
                submission_id, user_name
            )
            jobs.add(collect_job)

        store = create_gc3pie_sql_store()
        store.save(jobs)
        self.update_submission(jobs)
        engine = create_gc3pie_engine(store)
        logger.info('submit and monitor jobs')
        try:
            self.submit_jobs(
                jobs, engine, monitoring_depth=monitoring_depth,
                monitoring_interval=monitoring_interval
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
        help='''resubmits previously created jobs for "run" and "collect"
            phases to the cluster and monitors their status upon processing
        ''',
        monitoring_depth=Argument(
            type=int, help='number of child tasks that should be monitored',
            default=1, flag='d'
        ),
        monitoring_interval=Argument(
            type=int, help='seconds to wait between monitoring iterations',
            default=10, flag='i'
        )
    )
    def resubmit(self, monitoring_depth, monitoring_interval):
        self._print_logo()
        api = self.api_instance
        store = create_gc3pie_sql_store()
        job_id = self.get_task_id_of_last_submission()
        jobs = store.load(job_id)
        engine = create_gc3pie_engine(store)
        logger.info('resubmit and monitor jobs')
        try:
            self.submit_jobs(
                jobs, engine, monitoring_depth=monitoring_depth,
                monitoring_interval=monitoring_interval
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
