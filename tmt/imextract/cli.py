from . import logo
from . import __version__
from .api import ImageExtractor
from ..cli import CommandLineInterface
from ..cycle import Cycle


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
    def api_instance(self):
        '''
        Initialize an instance of class ImageExtractor with the parsed command
        line arguments.

        Returns
        -------
        ImageExtractor

        Raises
        ------
        OSError
            when metadata file does not exist

        See also
        --------
        `tmt.imextract.api.ImageExtractor`_
        '''
        cycle = Cycle(self.args.cycle_dir, self.args.cfg)
        return ImageExtractor(input_dir=cycle.image_upload_dir,
                              output_dir=cycle.image_dir,
                              metadata_file=cycle.image_metadata_file)

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
        `tmt.imextract.parser`_
        '''
        cli = ImExtract(args)
        getattr(cli, args.name)()
