from . import logo
from . import __version__
from .workflow import ClusterWorkflow
from .workflow import ClusterWorkflowManager
from .. import utils
from ..cli import CommandLineInterface
from ..experiment import Experiment

import logging
logger = logging.getLogger(__name__)


class Tmaps(CommandLineInterface):

    def __init__(self, args):
        super(Tmaps, self).__init__(args)
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
        manager = ClusterWorkflowManager(self.args.experiment_dir)
        experiment = Experiment(self.args.experiment_dir, self.cfg)
        self.__api_instance = ClusterWorkflow(
                    experiment=experiment,
                    no_shared_network=self.args.no_shared_network,
                    virtualenv=self.args.virtualenv,
                    verbosity=self.args.verbosity)
        logger.debug(
            'created an instance of API class "%s" and initialized it with '
            'the parsed command line arguments'
            % self.__api_instance.__class__.__name__)
        for step in manager.workflow_description['steps']:
            prog_name = step['prog_name']
            logger.debug('add step "%s" to the workflow' % prog_name)
            # main_args = manager.format_args(step['prog_args'])
            # logger.debug('parsed main arguments: {0}'.format(main_args))
            # init_args = manager.format_args(step['init_args'])
            # logger.debug('parsed init arguments: {0}'.format(init_args))
            prog_args = step['prog_args']
            init_args = step['init_args']
            self.__api_instance.add_step(prog_name, prog_args, init_args)
        return self.__api_instance

    def get_jobs(self):
        '''
        Combine GCPie "jobs" from different steps.

        Returns
        -------
        gc3libs.workflow.SequentialTaskCollection
            jobs
        '''
        api = self._api_instance
        jobs = api.create_jobs()
        return jobs

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
                     % (args.subparser_name, cli.__class__.__name__))
        getattr(cli, args.subparser_name)()
