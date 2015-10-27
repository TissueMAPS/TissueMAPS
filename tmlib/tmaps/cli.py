import logging
import argparse
from . import logo
from . import __version__
from .workflow import Workflow
from .api import WorkflowClusterRoutines
from ..experiment import Experiment

logger = logging.getLogger(__name__)


class Tmaps(object):

    def __init__(self, args):
        '''
        Initialize an instance of class Tmaps.

        
        '''
        self.args = args
        self.logger = logger

    @staticmethod
    def _print_logo():
        print logo % {'version': __version__}

    @property
    def name(self):
        '''
        Returns
        -------
        str
            name of the command line program
        '''
        return self.__class__.__name__.lower()

    @property
    def _api_instance(self):
        experiment = Experiment(self.args.experiment_dir)
        return WorkflowClusterRoutines(experiment, self.name)

    @staticmethod
    def call(args):
        '''
        Initialize an instance of the cli class with the parsed command
        line arguments and call the method matching the name of the subparser.

        Parameters
        ----------
        args: arparse.Namespace
            parsed command line arguments

        See also
        --------
        `tmlib.tmaps.argparser`_
        '''
        cli = Tmaps(args)
        logger.debug('call "%s" method of class "%s"'
                     % (args.method_name, cli.__class__.__name__))
        getattr(cli, args.method_name)()

    def submit(self):
        '''
        Initialize an instance of the API class corresponding to the program
        and process arguments of the "submit" subparser.
        '''
        api = self._api_instance
        jobs = Workflow(
                    experiment=api.experiment,
                    virtualenv=self.args.virtualenv,
                    verbosity=self.args.verbosity)
        api.submit_jobs(jobs, 5)

    @staticmethod
    def get_parser_and_subparsers(
            required_subparsers=['submit']):
        parser = argparse.ArgumentParser()
        parser.add_argument(
            'experiment_dir', help='path to experiment directory')
        parser.add_argument(
            '-v', '--verbosity', action='count', default=0,
            help='increase logging verbosity to DEBUG (default: INFO)')
        parser.add_argument(
            '-s', '--silent', action='store_true',
            help='set logging verbosity to WARNING')
        parser.add_argument(
            '--version', action='version')

        if not required_subparsers:
            raise ValueError('At least one subparser has to specified')

        subparsers = parser.add_subparsers(dest='method_name',
                                           help='sub-commands')

        if 'submit' in required_subparsers:
            submit_parser = subparsers.add_parser(
                'submit',
                help='submit and monitor jobs')
            submit_parser.description = '''
                Create jobs, submit them to the cluster, monitor their
                processing and collect their outputs.
            '''
            submit_parser.add_argument(
                '--interval', type=int, default=5,
                help='monitoring interval in seconds'
            )
            submit_parser.add_argument(
                '--virtualenv', type=str, default='tmaps',
                help='name of a virtual environment that should be activated '
                     '(default: tmaps')

        return (parser, subparsers)
