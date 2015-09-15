from . import logo
from . import __version__
from .api import PyramidCreation
from ..cli import CommandLineInterface
from ..experiment import Experiment


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
        return PyramidCreation(
                    experiment=experiment,
                    prog_name=self.name)

    @property
    def _variable_joblist_args(self):
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
        getattr(cli, args.subparser_name)()
