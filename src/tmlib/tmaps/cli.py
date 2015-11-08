import logging
from . import logo
from . import __version__
from .api import WorkflowClusterRoutines
from ..experiment import Experiment
from .. import cli

logger = logging.getLogger(__name__)


class Tmaps(object):

    '''
    Command line interface for submission of workflows.
    '''

    def __init__(self, experiment, verbosity):
        '''
        Initialize an instance of class Tmaps.

        Parameters
        ----------
        experiment: tmlib.experiment.Experiment
            configured experiment object
        verbosity: int
            logging level
        '''
        self.experiment = experiment
        self.verbosity = verbosity

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
        return WorkflowClusterRoutines(
                    experiment=self.experiment,
                    prog_name=self.name,
                    verbosity=self.verbosity)

    def submit(self, args):
        '''
        Initialize an instance of the API class corresponding to the program
        and process arguments provided by the "submit" subparser.

        Parameters
        ----------
        args: tmlib.args.SubmitArgs
            method-specific arguments
        '''
        logger.info('submit and monitor jobs')
        api = self._api_instance
        jobs = api.create_jobs(args.variable_args.stage,
                               args.variable_args.step)
        api.submit_jobs(jobs, args.interval, args.depth)

    def _call(self, args):
        method_args = cli.build_cli_method_args_from_mapping(
                            prog_name=self.name, **vars(args))
        cli.call_cli_method(self, args.method_name, method_args)

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
        :py:mod:`tmlib.metaextract.argparser`
        '''
        experiment = Experiment(args.experiment_dir)
        cli = Tmaps(experiment, args.verbosity)
        cli._call(args)

    @staticmethod
    def get_parser_and_subparsers(required_subparsers=['submit']):
        '''
        Get an argument parser object and subparser objects with default
        arguments for use in command line interfaces.
        The subparsers objects can be extended with additional subparsers and
        additional arguments can be added to each individual subparser.

        Parameters
        ----------
        required_subparsers: List[str]
            subparsers that should be returned (default: ``["submit"]``)

        Returns
        -------
        Tuple[argparse.Argumentparser and argparse._SubParsersAction]
            parser and subparsers objects
        '''
        return cli.CommandLineInterface.get_parser_and_subparsers(
                        required_subparsers=required_subparsers)
