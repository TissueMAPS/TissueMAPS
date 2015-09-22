from . import logo
from . import __version__
from .api import ImageRegistration
from ..cli import CommandLineInterface
from ..experiment import Experiment


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
        experiment = Experiment(self.args.experiment_dir, self.cfg)
        return ImageRegistration(
                    experiment=experiment,
                    shift_file_format_string=self.cfg['SHIFT_FILE'],
                    prog_name=self.name)

    @property
    def _variable_init_args(self):
        kwargs = dict()
        kwargs['batch_size'] = self.args.batch_size
        kwargs['ref_cycle'] = self.args.ref_cycle
        kwargs['ref_channel'] = self.args.ref_channel
        kwargs['max_shift'] = self.args.max_shift
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
        getattr(cli, args.subparser_name)()
