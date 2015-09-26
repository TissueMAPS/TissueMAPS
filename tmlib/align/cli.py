import logging
from . import logo
from . import __version__
from .api import ImageRegistration
from ..cli import CommandLineInterface

logger = logging.getLogger(__name__)


class Align(CommandLineInterface):

    def __init__(self, args):
        super(Align, self).__init__(args)
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
        self.__api_instance = ImageRegistration(
                    experiment_dir=self.args.experiment_dir,
                    shift_file_format_string=self.cfg['SHIFT_FILE'],
                    prog_name=self.name)
        logger.debug(
            'initialized API class "%s" with parsed arguments'
            % self.__api_instance.__class__.__name__)
        return self.__api_instance

    @property
    def _variable_init_args(self):
        kwargs = dict()
        kwargs['batch_size'] = self.args.batch_size
        kwargs['ref_cycle'] = self.args.ref_cycle
        kwargs['ref_channel'] = self.args.ref_channel
        kwargs['max_shift'] = self.args.max_shift
        return kwargs

    @property
    def _variable_apply_args(self):
        kwargs = dict()
        kwargs['illumcorr'] = self.args.illumcorr
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
        `tmlib.align.argparser`_
        '''
        cli = Align(args)
        logger.debug('call "%s" method of class "%s"'
                     % (args.subparser_name, cli.__class__.__name__))
        getattr(cli, args.subparser_name)()
