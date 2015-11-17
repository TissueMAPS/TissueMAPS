import logging
from . import logo
from . import __version__
from .api import WorkflowClusterRoutines
from ..experiment import Experiment
from .. import cli
from ..args import SubmitArgs
from ..args import ResumeArgs

logger = logging.getLogger(__name__)


class Tmaps(object):

    '''
    Command line interface for handling of workflows.
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
        logger.info('submit workflow')
        api = self._api_instance
        jobs = api.create_jobs(
                            start_stage=args.variable_args.stage,
                            start_step=args.variable_args.step)
        session = api.create_session(
                            jobs=jobs,
                            backup=args.variable_args.backup)
        api.submit_jobs(session, args.interval, args.depth)

    def resume(self, args):
        '''
        Initialize an instance of the API class corresponding to the program
        and process arguments provided by the "resume" subparser.

        Parameters
        ----------
        args: tmlib.args.ResumeArgs
            method-specific arguments
        '''
        logger.info('resume workflow')
        api = self._api_instance
        session = api.create_session(jobs=None, overwrite=False)
        api.submit_jobs(session, args.interval, args.depth)

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
        inst = Tmaps(experiment, args.verbosity)
        inst._call(args)

    @staticmethod
    def get_parser_and_subparsers(required_subparsers=['submit', 'resume']):
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
                                required_subparsers=[])

        submit_parser = subparsers.add_parser(
            'submit', help='submit and monitor a TissueMAPS workflow')
        submit_parser.description = '''
            Create a workflow, submit it to the cluster, monitor its
            processing and collect the outputs of individual steps.
        '''
        SubmitArgs._persistent_attrs = {'interval', 'depth'}
        SubmitArgs().add_to_argparser(submit_parser)

        resume_parser = subparsers.add_parser(
            'resume', help='resume a previously submitted workflow')
        resume_parser.description = '''
            Resume a workflow at a given stage/step.
        '''
        ResumeArgs().add_to_argparser(resume_parser)

        return (parser, subparsers)
