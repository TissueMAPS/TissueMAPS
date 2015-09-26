import logging
from . import logo
from . import __version__
from .api import MetadataConverter
from ..cli import CommandLineInterface

logger = logging.getLogger(__name__)


class Metaconvert(CommandLineInterface):

    '''
    Command line interface for metadata conversion.
    '''

    def __init__(self, args):
        '''
        Initialize an instance of class Metaconvert.

        Parameters
        ----------
        args: arparse.Namespace
            parsed command line arguments
        '''
        super(Metaconvert, self).__init__(args)
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
        logger.debug('parsed arguments: {0}'.format(self.args))
        self.__api_instance = MetadataConverter(
                            experiment_dir=self.args.experiment_dir,
                            file_format=self.args.format,
                            image_file_format_string=self.cfg['IMAGE_FILE'],
                            prog_name=self.name)
        logger.debug(
            'initialized API class "%s" with parsed arguments'
            % self.__api_instance.__class__.__name__)
        return self.__api_instance

    @staticmethod
    def call(args):
        '''
        Initializes an instance of class Metaconvert and calls the method
        that matches the name of the subparser with the parsed command
        line arguments.

        Parameters
        ----------
        args: arparse.Namespace
            parsed command line arguments
        '''
        cli = Metaconvert(args)
        logger.debug('call "%s" method of class "%s"'
                     % (args.subparser_name, cli.__class__.__name__))
        getattr(cli, args.subparser_name)()
