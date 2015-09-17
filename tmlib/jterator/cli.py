from . import logo
from . import __version__
from .api import ImageProcessingPipeline
from ..cli import CommandLineInterface
from ..experiment import Experiment


class Jterator(CommandLineInterface):

    def __init__(self, args):
        super(Jterator, self).__init__(args)
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
        return ImageProcessingPipeline(
                    experiment=experiment,
                    pipe_name=self.args.pipeline,
                    prog_name=self.name)

    @property
    def _variable_joblist_args(self):
        kwargs = dict()
        kwargs['batch_size'] = self.args.batch_size
        return kwargs

    def create(self):
        '''
        Initialize an instance of the API class corresponding to the specific
        command line interface and process arguments of the "create" subparser.
        '''
        print 'CREATE'
        api = self._api_instance
        api.create_project(self.args.repo_dir, self.args.skel_dir)

    def check(self):
        '''
        Initialize an instance of the API class corresponding to the specific
        command line interface and process arguments of the "check" subparser.
        '''
        print 'CHECK'
        api = self._api_instance
        api.check_pipeline()

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
        `tmlib.jterator.argparser`_
        '''
        cli = Jterator(args)
        getattr(cli, args.subparser_name)()
