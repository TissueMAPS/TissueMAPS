import logging
import argparse
from . import logo
from . import __version__
from .workflow import ClusterWorkflowManager
from .workflow import WorkflowClusterRoutines
from ..experiment import Experiment

logger = logging.getLogger(__name__)


class Tmaps(object):

    def __init__(self, args):
        self.args = args
        self.logger = logger

    @staticmethod
    def print_logo():
        print logo % {'version': __version__}

    @property
    def name(self):
        '''
        Returns
        -------
        str
            name of the program
        '''
        return self.__class__.__name__.lower()

    @property
    def _api_instance(self):
        logger.debug('parsed arguments: {0}'.format(self.args))
        experiment = Experiment(self.args.experiment_dir)
        self.__api_instance = ClusterWorkflowManager(
                    experiment=experiment,
                    virtualenv=self.args.virtualenv,
                    verbosity=self.args.verbosity)
        logger.debug(
            'instantiated API class "%s" with parsed arguments'
            % self.__api_instance.__class__.__name__)
        return self.__api_instance

    @staticmethod
    def call(args):
        '''
        Calls the method that matches the name of the specified subparser with
        the parsed command line arguments.

        Parameters
        ----------
        args: arparse.Namespace
            parsed command line arguments

        See also
        --------
        `tmlib.illuminati.argparser`_
        '''
        cli = Tmaps(args)
        logger.debug('call "%s" method of class "%s"'
                     % (args.method_name, cli.__class__.__name__))
        getattr(cli, args.method_name)()

    def submit(self):
        api = self._api_instance
        clst = WorkflowClusterRoutines(api.experiment, self.name)
        clst.submit_jobs(api, 5)

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
