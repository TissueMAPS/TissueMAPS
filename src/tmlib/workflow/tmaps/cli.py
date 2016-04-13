import logging

from tmlib.utils import same_docstring_as
from tmlib.workflow.tmaps import logo
from tmlib.workflow.tmaps.api import WorkflowManager
from tmlib.workflow import cli
from tmlib.workflow.args import SubmitArgs
from tmlib.workflow.args import ResubmitArgs

logger = logging.getLogger(__name__)


class Tmaps(object):

    '''Command line interface for building, submitting, and monitoring
    `TissueMAPS` workflows.
    '''

    def __init__(self, api_instance, verbosity):
        '''
        Parameters
        ----------
        api_instance: tmlib.workflow.tmaps.WorkflowManager
            instance of API class to which processing is delegated
        verbosity: int
            logging level
        '''
        self.api_instance = api_instance
        self.verbosity = verbosity

    @staticmethod
    def _print_logo():
        print logo

    @property
    def name(self):
        '''str: name of the step (command line program)'''
        return self.__class__.__name__.lower()

    def submit(self, args):
        '''Processes arguments provided by the "submit" subparser.

        Parameters
        ----------
        args: tmlib.args.SubmitArgs
            method-specific arguments
        '''
        self._print_logo()
        logger.info('submit workflow')
        api = self.api_instance
        workflow = api.create_workflow(
            waiting_time=args.variable_args.wait
        )
        session = api.create_gc3pie_session()
        logger.debug('add jobs to session "%s"', session.name)
        session.add(workflow)
        session.save_all()
        logger.debug('add session to engine store')
        engine = api.create_gc3pie_engine()
        engine._store = session.store
        logger.info('submit and monitor jobs')
        try:
            api.submit_jobs(workflow, engine, args.interval, args.depth)
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

    def resubmit(self, args):
        '''Processes arguments provided by the "resubmit" subparser.

        Parameters
        ----------
        args: tmlib.args.ResubmitArgs
            method-specific arguments
        '''
        self._print_logo()
        api = self.api_instance
        session = api.create_gc3pie_session()
        logger.debug('load jobs from session "%s"', session.name)
        job_ids = session.list_ids()
        workflow = session.load(int(job_ids[-1]))
        workflow.start_stage = args.variable_args.stage
        logger.debug('add session to engine store')
        engine = api.create_gc3pie_engine()
        engine._store = session.store
        logger.info('resubmit and monitor jobs')
        try:
            api.submit_jobs(workflow, engine, args.interval, args.depth)
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

    def _call(self, args):
        method_args = cli.create_method_args(
            step_name=self.name, **vars(args)
        )
        getattr(self, args.method_name)(method_args)

    @staticmethod
    @same_docstring_as(cli.CommandLineInterface.call)
    def call(name, args):
        api_instance = WorkflowManager(
            args.experiment_id, args.verbosity
        )
        Tmaps(api_instance, args.verbosity)._call(args)

    @staticmethod
    def main(parser):
        '''Main entry point for command line interface.

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
        cli.CommandLineInterface.main(parser)

    @staticmethod
    def get_parser_and_subparsers(methods={'submit', 'resume'}):
        '''
        Get an argument parser object and subparser objects with default
        arguments for use in command line interfaces.
        The subparsers objects can be extended with additional subparsers and
        additional arguments can be added to each individual subparser.

        Parameters
        ----------
        required_subparsers: List[str]
            subparsers that should be returned
            (default: ``["submit", "resume"]``)

        Returns
        -------
        Tuple[argparse.Argumentparser and argparse._SubParsersAction]
            parser and subparsers objects
        '''
        parser, subparsers = cli.CommandLineInterface.get_parser_and_subparsers(
                                methods={})

        submit_parser = subparsers.add_parser(
            'submit', help='create, submit and monitor a workflow')
        submit_parser.description = '''
            Create a workflow, submit it to the cluster and monitor its
            processing.
        '''
        SubmitArgs().add_to_argparser(
            submit_parser, ignore={'memory', 'duration'}
        )

        resubmit_parser = subparsers.add_parser(
            'resubmit', help='resubmit and monitor an already created workflow')
        resubmit_parser.description = '''
            Resubmit an already created workflow to the cluster and monitor
            its processing.
        '''
        ResubmitArgs().add_to_argparser(resubmit_parser)

        return (parser, subparsers)
