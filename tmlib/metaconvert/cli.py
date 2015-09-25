from . import logo
from . import __version__
from .api import MetadataConverter
from ..cli import CommandLineInterface
from ..experiment import Experiment


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
        experiment = Experiment(self.args.experiment_dir, self.cfg)
        return MetadataConverter(
                    experiment=experiment,
                    file_format=self.args.format,
                    image_file_format_string=self.cfg['IMAGE_FILE'],
                    prog_name=self.name)

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
        getattr(cli, args.subparser_name)()
