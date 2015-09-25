from . import logo
from . import __version__
from .api import PyramidCreation
from ..cli import CommandLineInterface
from ..experiment import Experiment
import logging
logger = logging.getLogger(__name__)


class Illuminati(CommandLineInterface):

    def __init__(self, args):
        super(Illuminati, self).__init__(args)
        self.args = args

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
        experiment = Experiment(self.args.experiment_dir, self.cfg)
        logger.debug('created an instance of configuration class "%s"'
                     % experiment.__class__.__name__)
        self.__api_instance = PyramidCreation(
                                experiment=experiment, prog_name=self.name)
        logger.debug(
            'created an instance of API class "%s" and initialized it with '
            'the parsed command line arguments'
            % self.__api_instance.__class__.__name__)
        return self.__api_instance

    @property
    def _variable_init_args(self):
        kwargs = dict()
        kwargs['shift'] = self.args.shift
        kwargs['illumcorr'] = self.args.illumcorr
        kwargs['thresh'] = self.args.thresh
        kwargs['thresh_value'] = self.args.thresh_value
        kwargs['thresh_percent'] = self.args.thresh_percent
        return kwargs

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
        cli = Illuminati(args)
        logger.debug('call "%s" method of class "%s"'
                     % (args.subparser_name, cli.__class__.__name__))
        getattr(cli, args.subparser_name)()
