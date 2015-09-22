import logging
from . import logo
from . import __version__
from .api import PyramidCreation
from ..cli import CommandLineInterface
from ..experiment import Experiment
from .. import logging_utils


class Illuminati(CommandLineInterface):

    def __init__(self, args):
        super(Illuminati, self).__init__(args)
        self.args = args
        self.configure_logging()

    def configure_logging(self):
        self.logger = logging.getLogger(self.name)
        logging.basicConfig(
            level=logging_utils.map_log_verbosity(self.args.verbosity),
            format='%(asctime)s %(name)-5s %(levelname)-5s %(message)s',
            datefmt='%m-%d %H:%M')
        # TODO: dependent on `verbosity`
        for handler in logging.root.handlers:
            handler.addFilter(logging_utils.Whitelist(self.__class__.__name__,
                              'PyramidCreation', 'ChannelLayer'))

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
        self.logger.info('%s' % self.name.upper())
        experiment = Experiment(self.args.experiment_dir, self.cfg)
        return PyramidCreation(
                    experiment=experiment,
                    prog_name=self.name)

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
        getattr(cli, args.subparser_name)()
