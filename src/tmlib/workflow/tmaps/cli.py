import argparse
import inspect
import logging

import tmlib.models as tm
from tmlib import __version__
from tmlib.utils import same_docstring_as
from tmlib.workflow.tmaps import logo
from tmlib.logging_utils import map_logging_verbosity
from tmlib.logging_utils import configure_logging
from tmlib.workflow.utils import create_gc3pie_engine
from tmlib.workflow.utils import create_gc3pie_sql_store
from tmlib.workflow.submission import SubmissionManager
from tmlib.workflow.tmaps.api import WorkflowManager
from tmlib.errors import NotSupportedError
from tmlib.errors import WorkflowDescriptionError
from tmlib.workflow import cli

logger = logging.getLogger(__name__)


class Tmaps(SubmissionManager):

    '''Command line interface for building, submitting, and monitoring
    `TissueMAPS` workflows.
    '''

    def __init__(self, api_instance):
        '''
        Parameters
        ----------
        api_instance: tmlib.workflow.tmaps.WorkflowManager
            instance of API class to which processing is delegated
        '''
        self.api_instance = api_instance
        super(Tmaps, self).__init__(self.api_instance.experiment_id, self.name)

    @staticmethod
    def _print_logo():
        print logo

    @property
    def name(self):
        '''str: name of the step (command line program)'''
        return 'workflow'
        # return self.__class__.__name__.lower()

    def submit(self, monitoring_depth, monitoring_interval):
        '''Create workflow, submit it to the cluster and monitor its progress.

        Parameters
        ----------
        monitoring_depth: int
            number of child tasks that should be monitored
        '''
        self._print_logo()
        logger.info('submit workflow')
        api = self.api_instance
        submission_id, user_name = self.register_submission('workflow')
        workflow = api.create_workflow(submission_id, user_name)
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
        '''Resumit previously created workflow to the cluster and monitor
        its status.

        Parameters
        ----------
        monitoring_depth: int
            number of child tasks that should be monitored
        stage: str
            stage at which workflow should be submitted
        '''
        self._print_logo()
        api = self.api_instance
        store = create_gc3pie_sql_store()
        task_id = self.get_task_id_of_last_submission()
        with tm.utils.MainSession() as session:
            experiment_ref = session.query(tm.ExperimentReference).\
                get(self.experiment_id)
            workflow_description = experiment_ref.workflow_description
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
    def main(cls):
        '''Main entry point for command line interface.

        Parsers the command line arguments and configures logging.

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

        args = parser.parse_args()

        configure_logging()
        logger = logging.getLogger('tmlib')
        level = map_logging_verbosity(args.verbosity)
        logger.setLevel(level)

        # Silence some chatty loggers
        gc3libs_logger = logging.getLogger('gc3.gc3libs')
        gc3libs_logger.setLevel(logging.CRITICAL)

        api_instance = WorkflowManager(args.experiment_id, args.verbosity)
        cli_instance = cls(api_instance)
        cli_instance(args)
