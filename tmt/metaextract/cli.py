from . import logo
from . import __version__
from .api import OmeXmlExtractor
from ..cli import CommandLineInterface
from ..cycle import Cycle


class MetaExtract(CommandLineInterface):

    '''
    Command line interface for extraction of metadata from image files.
    '''

    def __init__(self, args):
        super(MetaExtract, self).__init__(args)
        self.args = args

    @staticmethod
    def print_logo():
        print logo % {'version': __version__}

    @property
    def api_instance(self):
        '''
        Initialize an instance of class OmeXmlExtractor with the parsed command
        line arguments.

        Returns
        -------
        OmeXmlExtractor

        See also
        --------
        `tmt.metaextract.api.OmeXmlExtractor`_
        '''
        cycle = Cycle(self.args.cycle_dir, self.args.cfg)
        return OmeXmlExtractor(input_dir=cycle.image_upload_dir,
                               output_dir=cycle.ome_xml_dir)

    def collect(self):
        print 'COLLECT'
        api = self.api_instance
        print '.  copy extracted metadata from standard output'
        api.collect_extracted_metadata()

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
        `tmt.metaextract.parser`_
        '''
        cli = MetaExtract(args)
        getattr(cli, args.name)()
