# TmLibrary - TissueMAPS library for distibuted image analysis routines.
# Copyright (C) 2016-2018 University of Zurich.
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
import argparse
import inspect
import logging

import tmlib.models as tm
from tmlib import __version__
from tmlib.utils import same_docstring_as
from tmlib.log import map_logging_verbosity
from tmlib.log import configure_logging
from tmlib.workflow.utils import create_gc3pie_engine
from tmlib.workflow.utils import create_gc3pie_sql_store
from tmlib.workflow.workflow import Workflow
from tmlib.workflow.submission import WorkflowSubmissionManager
from tmlib.errors import NotSupportedError
from tmlib.errors import WorkflowDescriptionError
from tmlib.workflow import cli

logger = logging.getLogger(__name__)



class WorkflowManager(WorkflowSubmissionManager):

    '''Command line interface for submitting, and monitoring
    `TissueMAPS` workflows.
    '''

    def __init__(self, experiment_id, verbosity):
        '''
        Parameters
        ----------
        experiment_id: int
            ID of the processed experiment
        verbosity: int
            logging verbosity level
        '''
        self.experiment_id = experiment_id
        self.verbosity = verbosity
        super(WorkflowManager, self).__init__(self.experiment_id, 'workflow')

    @staticmethod
    def _print_logo():
        print '''
             _        _        _        _        _        _        _        _
           _( )__   _( )__   _( )__   _( )__   _( )__   _( )__   _( )__   _( )__
         _|     _|_|     _|_|     _|_|     _|_|     _|_|     _|_|     _|_|     _|      TissueMAPS workflow manager (tmlib %s)
        (_ W _ (_(_ O _ (_(_ R _ (_(_ K _ (_(_ F _ (_(_ L _ (_(_ O _ (_(_ W _ (_       https://github.com/TissueMAPS/TmLibrary
          |_( )__| |_( )__| |_( )__| |_( )__| |_( )__| |_( )__| |_( )__| |_( )__|

        ''' % __version__

    def submit(self, monitoring_depth, monitoring_interval, force=False):
        '''Creates a workflow, submits it to the cluster and monitors its
        progress.

        Parameters
        ----------
        monitoring_depth: int
            number of child tasks that should be monitored
        monitoring_interval: int
            query status of jobs every `monitoring_interval` seconds
        force: bool, opional
            whether inactivated stages and steps should be submitted anyways
        '''
        self._print_logo()
        logger.info('submit workflow')
        submission_id, user_name = self.register_submission()
        with tm.utils.ExperimentSession(self.experiment_id) as session:
            experiment = session.query(tm.Experiment).get(self.experiment_id)
            workflow_description = experiment.workflow_description
        if force:
            for stage in workflow_description.stages:
                stage.active = True
                for step in stage.steps:
                    step.active = True
        workflow = Workflow(
            experiment_id=self.experiment_id,
            verbosity=self.verbosity,
            submission_id=submission_id,
            user_name=user_name,
            description=workflow_description
        )
        store = create_gc3pie_sql_store()
        store.save(workflow)
        self.update_submission(workflow)
        engine = create_gc3pie_engine(store)
        logger.info('submit and monitor jobs')
        try:
            self.submit_jobs(
                workflow, engine,
                monitoring_depth=monitoring_depth,
                monitoring_interval=monitoring_interval
            )
        except KeyboardInterrupt:
            logger.info('processing interrupted')
            logger.info('killing jobs')
            while True:
                engine.kill(workflow)
                engine.progress()
                if workflow.is_terminated:
                    break
        except:
            raise

    def resubmit(self, monitoring_depth, stage):
        '''Resumits a previously created workflow to the cluster and monitors
        its status.

        Parameters
        ----------
        monitoring_depth: int
            number of child tasks that should be monitored
        stage: str
            stage at which workflow should be submitted
        '''
        self._print_logo()
        store = create_gc3pie_sql_store()
        task_id = self.get_task_id_of_last_submission()
        with tm.utils.ExperimentSession(self.experiment_id) as session:
            experiment = session.query(tm.Experiment).get(self.experiment_id)
            workflow_description = experiment.workflow_description
        workflow = store.load(task_id)
        workflow.update_description(workflow_description)
        stage_names = [s.name for s in workflow.description.stages]
        try:
            start_index = stage_names.index(stage)
            workflow.update_stage(start_index)
        except IndexError:
            raise WorkflowDescriptionError('Unknown stage "%s".' % stage)
        logger.info('resubmit workflow at stage #%d "%s"', start_index, stage)
        engine = create_gc3pie_engine(store)
        logger.info('resubmit and monitor jobs')
        try:
            self.submit_jobs(
                workflow, engine, start_index=start_index,
                monitoring_depth=monitoring_depth
            )
        except KeyboardInterrupt:
            logger.info('processing interrupted')
            logger.info('killing jobs')
            while True:
                engine.kill(workflow)
                engine.progress()
                if workflow.is_terminated:
                    break
        except:
            raise

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
            'call "%s" method with the parsed arguments', cli_args.method
        )
        # Strip the relevant arguments from the namespace
        method = getattr(self, cli_args.method)
        arg_names = inspect.getargspec(method).args[1:]
        arg_defaults = inspect.getargspec(method).defaults
        method_args = dict()
        for name in arg_names:
            logger.debug(
                'pass argument "%s" to method "%s"', name, cli_args.method
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
        method(**method_args)

    @classmethod
    def _get_parser(cls):
        parser = argparse.ArgumentParser()
        parser.description = cls.__doc__
        parser.version = __version__
        parser.add_argument(
            'experiment_id', type=int,
            help='ID of the experiment that should be processed'
        )
        parser.add_argument(
            '--verbosity', '-v', action='count', default=0,
            help='increase logging verbosity'
        )
        subparsers = parser.add_subparsers(dest='method', help='methods')
        subparsers.required = True

        submit_help = '''create a workflow, submit it to the cluster and
            monitor its status
        '''
        submit_parser = subparsers.add_parser('submit', help=submit_help)
        submit_parser.description = submit_help
        submit_parser.add_argument(
            '--monitoring_depth', '-d', type=int, default=2,
            help='number of child tasks that should be monitored (default: 2)'
        )
        submit_parser.add_argument(
            '--monitoring_interval', '-i', type=int, default=10,
            help='interval for monitoring interations (default: 10)'
        )
        submit_parser.add_argument(
            '--force', '-f', action='store_true',
            help='also submit inactivated stages and steps'
        )

        resubmit_help = '''resubmit a previously created workflow to the
            cluster and monitor its status
        '''
        resubmit_parser = subparsers.add_parser('resubmit', help=resubmit_help)
        resubmit_parser.description = resubmit_help
        resubmit_parser.add_argument(
            '--monitoring_depth', '-m', type=int, default=2,
            help='number of child tasks that should be monitored (default: 2)'
        )
        resubmit_parser.add_argument(
            '--monitoring_interval', '-i', type=int, default=10,
            help='interval for monitoring interations (default: 10)'
        )
        resubmit_parser.add_argument(
            '--stage', '-s', type=str, required=True,
            help='stage at which workflow should be resubmitted'
        )
        return parser

    @classmethod
    def __main__(cls):
        '''Main entry point for command line interface.

        Parsers the command line arguments and configures logging.

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
        parser = cls._get_parser()
        args = parser.parse_args()

        configure_logging()
        logger = logging.getLogger('tmlib')
        level = map_logging_verbosity(args.verbosity)
        logger.setLevel(level)

        # Silence some chatty loggers
        gc3libs_logger = logging.getLogger('gc3.gc3libs')
        if args.verbosity < 3:
            gc3libs_logger.setLevel(logging.ERROR)
        elif args.verbosity < 4:
            gc3libs_logger.setLevel(logging.WARNING)
        elif args.verbosity < 5:
            gc3libs_logger.setLevel(logging.INFO)
        else:
            gc3libs_logger.setLevel(logging.DEBUG)

        cli_instance = cls(args.experiment_id, args.verbosity)
        cli_instance(args)
