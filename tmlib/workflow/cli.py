# TmLibrary - TissueMAPS library for distibuted image analysis routines.
# Copyright (C) 2016, 2018  University of Zurich
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
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
from tmlib.workflow.submission import WorkflowSubmissionManager
from tmlib.workflow.workflow import WorkflowStep
from tmlib.workflow.jobs import IndependentJobCollection
from tmlib.log import configure_logging
from tmlib.log import map_logging_verbosity
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
        BatchArgs, SubmissionArgs = get_step_args(step_name)
        subparsers = parser.add_subparsers(dest='method', help='methods')
        subparsers.required = True
        # flags = collections.defaultdict(list)
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
                        # if arg.flag is not None:
                        #     flags[attr_name].append(arg.flag)
                        # if arg.short_flag is not None:
                        #     flags[attr_name].append(arg.short_flag)
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
                # if arg.flag is not None:
                #     flags[attr_name].append(arg.flag)
                # if arg.short_flag is not None:
                #     flags[attr_name].append(arg.short_flag)

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


class WorkflowStepCLI(WorkflowSubmissionManager):

    '''Abstract base class for command line interfaces.

    Each workflow step must implement this class. The derived class will get
    automatically equipped with command line interface functionality
    in form of an instance of `argparse.ArgumentParser`.
    The docstring of the derived class is also used for the *description*
    attribute of the parser for display in the command line.
    A separate subparser is added for each method of the derived class that is
    decorated with :func:`climethod <tmlib.workflow.climethod>`. The decorator
    provides descriptions of the method arguments, which are also added to the
    corresponding subparser.

    The :meth:`init <tmlib.workflow.cli.WorkflowStepCLI.init>`
    and :meth:`submit <tmlib.workflow.cli.CommandLineInterace.submit>` methods
    require additional step-specific arguments that are passed to the *API*
    methods
    :meth:`create_run_batches <tmlib.workflow.api.WorkflowStepAPI.create_run_batches>`
    and
    :meth:`create_run_jobs <tmlib.workflow.api.WorkflowStepAPI.create_run_jobs>`,
    respectively. These arguments are handled separately, since they also need
    to be accessible outside the scope of the command line interace.
    They are provided by step-specific implementations of
    :class:`BatchArguments <tmlib.workflow.args.BatchArguments>` and
    :class:`SubmissionArguments <tmlib.workflow.args.SubmissionArguments>`
    and added to the corresponding *init* and *submit* subparsers, respectively.
    '''

    __metaclass__ = _CliMeta

    __abstract__ = True

    def __init__(self, api_instance, verbosity):
        '''
        Parameters
        ----------
        api_instance: tmlib.api.WorkflowStepAPI
            instance of API class to which processing is delegated
        verbosity: int
            logging verbosity level
        '''
        self.api_instance = api_instance
        self.verbosity = verbosity
        super(WorkflowStepCLI, self).__init__(
            api_instance.experiment_id, self.name
        )

    @property
    def name(self):
        '''str: name of the step (command line program)'''
        return self.__class__.__name__.lower()

    @classmethod
    def __main__(cls):
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
        # Adapt level of GC3Pie logger, which is very chatty.
        gc3libs_logger = logging.getLogger('gc3.gc3libs')
        if arguments.verbosity > 4:
            gc3libs_logger.setLevel(logging.DEBUG)
        elif arguments.verbosity == 4:
            gc3libs_logger.setLevel(logging.INFO)
        else:
            gc3libs_logger.setLevel(logging.ERROR)
        # same for SQLAlchemy
        sqlalchemy_logger = logging.getLogger('sqlalchemy.engine')
        if arguments.verbosity > 3:
            sqlalchemy_logger.setLevel(logging.DEBUG)
        elif arguments.verbosity > 2:
            sqlalchemy_logger.setLevel(logging.INFO)
        elif arguments.verbosity > 1:
            sqlalchemy_logger.setLevel(logging.WARNING)
        else:
            sqlalchemy_logger.setLevel(logging.ERROR)

        logger.debug('processing on node: %s', socket.gethostname())
        logger.debug('running program: %s' % cls.__name__.lower())

        # Use only a single database connection for the job.
        # This is necessary on a large cluster to prevent too many concurrent
        # connections by parallel running jobs, which would overload the
        # database server.
        # Using more than one connection also wouldn't be of any help, since
        # the job runs in a single process, such that the same connection can
        # be reused.
        tm.utils.set_pool_size(1)

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
            cli_instance = cls(api_instance, arguments.verbosity)
            cli_instance(arguments)
            logger.info('JOB COMPLETED')
            sys.exit(0)
            return 0
        except Exception as error:
            sys.stderr.write('\nJOB FAILED:\n%s\n' % str(error))
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
                        'use default value for argument "%s" for method "%s" '
                        'of class "%s"',
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
        help=(
            'cleans up the output of a previous submission, i.e. removes '
            'files and database entries created by previously submitted jobs'
        )
    )
    def cleanup(self):
        self._print_logo()
        self.api_instance.delete_previous_job_output()

    @climethod(
        help=(
            'creates batches for parallel processing and thereby '
            'defines how the computational task should be distrubuted over '
            'the cluster (also cleans up the output of previous submissions)'
        )
    )
    def init(self):
        self._print_logo()
        api = self.api_instance
        logger.debug('remove batches of previous submission')
        shutil.rmtree(api.batches_location)
        os.mkdir(api.batches_location)
        logger.info('delete previous job output')
        api.delete_previous_job_output()
        logger.info('create batches for run jobs')
        batches = api.create_run_batches(self._batch_args)
        for index, batch in enumerate(batches):
            api.store_run_batch(batch, index+1)
        if api.has_collect_phase:
            logger.info('create batch for collect job')
            batch = api.create_collect_batch(self._batch_args)
            api.store_collect_batch(batch)

    @climethod(
        help='runs an invidiual batch job on the local machine',
        job_id=Argument(
            type=int, help='ID of the job that should be run',
            flag='job', short_flag='j'
        ),
        assume_clean_state=Argument(
            type=bool,
            help='assume that previous outputs have been cleaned up',
            flag='assume-clean-state', default=False
        )
    )
    def run(self, job_id, assume_clean_state):
        self._print_logo()
        api = self.api_instance
        batch = api.get_run_batch(job_id)
        logger.info('run job #%d' % job_id)
        api.run_job(batch, assume_clean_state)

    @climethod(
        help='prints the description of a given batch job to the console',
        phase=Argument(
            type=str, short_flag='p', choices={'run', 'collect'},
            help='phase of the workflow step to which the job belongs'
        ),
        job_id=Argument(
            type=int, flag='job', short_flag='j', dependency=('phase', 'run'),
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
            batch = api.get_run_batch(job_id)
        else:
            batch = api.get_collect_batch()
        print('\nJOB DESCRIPTION\n===============\n\n%s'
              % yaml.safe_dump(batch, default_flow_style=False))

    @climethod(
        help='prints the log output of a given batch job to the console',
        phase=Argument(
            type=str, choices={'init', 'run', 'collect'}, short_flag='p',
            required=True,
            help='phase of the workflow step to which the job belongs'
        ),
        job_id=Argument(
            type=int, flag='job', short_flag='j', dependency=('phase', 'run'),
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
        log = api.get_log_output(phase, job_id)
        print('\nOUTPUT\n======\n\n%s\n\nERROR\n=====\n\n%s'
              % (log['stdout'], log['stderr']))

    @climethod(
        help=(
            'creates batch jobs for the "run" and "collect" phases, submits '
            'them to the cluster and monitors their status upon processing '
            '(requires a prior "init")'
        ),
        monitoring_depth=Argument(
            type=int, help='number of child tasks that should be monitored',
            meta='INDEX', default=1, flag='depth', short_flag='d'
        ),
        monitoring_interval=Argument(
            type=int, help='seconds to wait between monitoring iterations',
            meta='SECONDS', default=10, flag='interval', short_flag='i'
        )
    )
    def submit(self, monitoring_depth, monitoring_interval):
        self._print_logo()
        submission_id, user_name = self.register_submission()
        api = self.api_instance

        jobs = IndependentJobCollection(api.step_name, submission_id)
        run_job_collection = api.create_run_phase(
            submission_id, jobs.persistent_id
        )
        run_jobs = api.create_run_jobs(
            user_name, run_job_collection, self.verbosity,
            duration=self._submission_args.duration,
            memory=self._submission_args.memory,
            cores=self._submission_args.cores
        )
        jobs.add(run_jobs)
        if api.has_collect_phase:
            collect_job_collection = api.create_collect_phase(
                submission_id, jobs.persistent_id
            )
            collect_job = api.create_collect_job(
                user_name, collect_job_collection, self.verbosity
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
        help=(
            'resubmits previously created jobs for "run" and "collect" '
            'phases to the cluster and monitors their status upon processing '
        ),
        monitoring_depth=Argument(
            type=int, help='number of child tasks that should be monitored',
            meta='INDEX', default=1, flag='depth', short_flag='d'
        ),
        monitoring_interval=Argument(
            type=int, help='seconds to wait between monitoring iterations',
            meta='SECONDS', default=10, flag='interval', short_flag='i'
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
        help=(
            'collects the output of run jobs, i.e. performs a '
            'post-processing operation that either cannot be parallelized '
            'or needs to be performed afterwards'
        )
    )
    def collect(self):
        self._print_logo()
        api = self.api_instance
        logger.info('read job description from file')
        batch = api.get_collect_batch()
        logger.info('collect job output')
        api.collect_job_output(batch)
