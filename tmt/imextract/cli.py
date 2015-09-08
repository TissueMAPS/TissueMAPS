from . import logo
from . import __version__
from .api import ImageExtractor
from ..cli import CommandLineInterface
from ..experiment import Experiment


class ImExtract(CommandLineInterface):

    '''
    Command line interface for extraction of images from image files.
    '''

    def __init__(self, args):
        super(ImExtract, self).__init__(args)
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
        return ImageExtractor(experiment=experiment, prog_name=self.name)

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
        `tmt.imextract.argparser`_
        '''
        cli = ImExtract(args)
        getattr(cli, args.subparser_name)()
