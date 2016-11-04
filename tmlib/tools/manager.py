import os
import argparse
import socket
import logging
from whichcraft import which
from gc3libs.quantity import Duration
from gc3libs.quantity import Memory

from tmlib import __version__
from tmlib import cfg
import tmlib.models as tm
from tmlib.submission import SubmissionManager
from tmlib.tools.jobs import ToolJob
from tmlib.writers import JsonWriter
from tmlib.readers import JsonReader
from tmlib.utils import autocreate_directory_property
from tmlib.logging_utils import configure_logging, map_logging_verbosity
from tmlib.tools import get_tool_class, get_available_tools

logger = logging.getLogger(__name__)



class ToolRequestManager(SubmissionManager):

    '''Command line interface for handling `TissueMAPS` tool requests.'''

    def __init__(self, experiment_id, tool_name, verbosity):
        '''
        Parameters
        ----------
        experiment_id: int
            ID of the processed experiment
        tool_name: str
            name of the corresponding tool
        verbosity: int
            logging verbosity level
        '''
        self.experiment_id = experiment_id
        self.verbosity = verbosity
        self.tool_name = tool_name
        super(ToolRequestManager, self).__init__(self.experiment_id, 'tool')
        with tm.utils.MainSession() as session:
            experiment = session.query(tm.ExperimentReference).\
                get(self.experiment_id)
            self.tools_location = experiment.tools_location

    @staticmethod
    def _print_logo():
        print '''
            )           (
         ( /(           )\\
         )\()) (    (  ((_)
        (_))/  )\   )\  _     TissueMAPS tool request manager (tmlib %s)
        | |_  ((_) ((_)| |    https://github.com/TissueMAPS/TmLibrary
        |  _|/ _ \/ _ \| |
         \__|\___/\___/|_|

        ''' % __version__

    @autocreate_directory_property
    def batches_location(self):
        return os.path.join(self.tools_location, 'batches')

    @autocreate_directory_property
    def log_location(self):
        return os.path.join(self.tools_location, 'logs')

    def _build_batch_filename_for_job(self, submission_id):
        filename = '%s_%d.json' % (self.__class__.__name__, submission_id)
        return os.path.join(self.batches_location, filename)

    def _build_command(self, submission_id):
        if cfg.tool_library == 'spark':
            command = [
                'spark-submit',
                '--driver-class-path', cfg.spark_jdbc_driver,
                '--master', cfg.spark_master,
            ]
            if cfg.spark_master == 'yarn':
                command.extend(['--deploy-mode', 'client'])
            # args.extend([
            #     '--py-files', os.path.expanduser('~/tmlibrary/tmlibrary-egg.info')
            # ])
        else:
            command = []

        command.extend([
            which('tm_tool.py'),
            str(self.experiment_id),
            '--name', self.tool_name,
            '--submission_id', str(submission_id)
        ])
        command.extend(['-v' for x in xrange(self.verbosity)])
        logger.debug('submit tool request: %s', ' '.join(command))
        print ' '.join(command)
        return command

    def create_job(self, submission_id, user_name, duration='00:30:00',
            memory=3800, cores=1):
        '''Creates a job for asynchroneous processing of a client tool request.

        Parameters
        ----------
        submission_id: int
            ID of the corresponding submission
        user_name: str
            name of the submitting user
        duration: str, optional
            computational time that should be allocated for the job
            in HH:MM:SS format (default: ``"00:30:00"``)
        memory: int, optional
            amount of memory in Megabyte that should be allocated for the job
            (default: ``3800``)
        cores: int, optional
            number of CPU cores that should be allocated for the job
            (default: ``1``)

        Returns
        -------
        tmlib.tools.jobs.ToolJob
            tool job
        '''
        logger.info('create tool job for submission %d', submission_id)
        logger.debug('allocated time for job: %s', duration)
        logger.debug('allocated memory for job: %d MB', memory)
        logger.debug('allocated cores for job: %d', cores)
        job = ToolJob(
            tool_name=self.tool_name,
            # TODO: tool_name
            arguments=self._build_command(submission_id),
            output_dir=self.log_location,
            submission_id=submission_id,
            user_name=user_name
        )
        job.requested_walltime = Duration(duration)
        # TODO: this might need to be increased for scikit learn jobs
        job.requested_memory = Memory(memory, Memory.MB)
        if not isinstance(cores, int):
            raise TypeError(
                'Argument "cores" must have type int.'
            )
        if not cores > 0:
            raise ValueError(
                'The value of "cores" must be positive.'
            )
        job.requested_cores = cores
        return job

    def read_batch_file(self, submission_id):
        '''Reads job description from JSON file.

        Parameters
        ----------
        submission_id: int
            ID of the respective submission

        Returns
        -------
        dict
            batch

        Raises
        ------
        OSError
            when `filename` does not exist
        '''
        filename = self._build_batch_filename_for_job(submission_id)
        if not os.path.exists(filename):
            raise OSError(
                'Job description file does not exist: %s.' % filename
            )
        with JsonReader(filename) as f:
            batch = f.read()
        return batch

    @autocreate_directory_property
    def log_location(self):
        '''str: location where log files are stored'''
        return os.path.join(self.tools_location, 'log')

    @autocreate_directory_property
    def batches_location(self):
        '''str: location where job description files are stored'''
        return os.path.join(self.tools_location, 'batches')

    def write_batch_file(self, batch, submission_id):
        '''Writes job description to file in JSON format.

        Parameters
        ----------
        batch: dict
            job description as a mapping of key-value pairs
        submission_id: int
            ID of the corresponding submission

        Raises
        ------
        TypeError
            when `batch` is not a mapping
        '''
        if not isinstance(batch, dict):
            raise TypeError(
                'Job description must have type dict.'
            )
        batch_file = self._build_batch_filename_for_job(submission_id)
        with JsonWriter(batch_file) as f:
            f.write(batch)

    @classmethod
    def _get_parser(cls):
        parser = argparse.ArgumentParser()
        parser.description = '''
            TissueMAPS command line interface for asynchronous processing of
            client tool requests.
        '''
        parser.add_argument(
            'experiment_id', type=int,
            help='ID of the experiment that should be processed'
        )
        parser.add_argument(
            '--verbosity', '-v', action='count', default=0,
            help='increase logging verbosity'
        )
        parser.add_argument(
            '--name', '-n', required=True,
            choices=set(get_available_tools()), help='name of the tool'
        )
        parser.add_argument(
            '--submission_id', '-s', type=int, required=True,
            help='ID of the corresponding tool job submission'
        )
        return parser

    @classmethod
    def main(cls):
        '''Main entry point for command line interface.

        Parsers the command line arguments and configures logging.

        Returns
        -------
        int
            ``0`` when program completes successfully and ``1`` otherwise

        Raises
        ------
        SystemExit
            exitcode ``1`` when the call raises an :class:`Exception`

        Warning
        -------
        Don't do any other logging configuration anywhere else!
        '''
        parser = cls._get_parser()
        args = parser.parse_args()

        configure_logging()
        level = map_logging_verbosity(args.verbosity)
        lib_logger = logging.getLogger('tmlib')
        lib_logger.setLevel(level)
        logger.debug('processing on node: %s', socket.gethostname())

        manager = cls(args.experiment_id, args.name, args.verbosity)
        manager._print_logo()
        payload = manager.read_batch_file(args.submission_id)
        tool_cls = get_tool_class(args.name)
        tool = tool_cls(args.experiment_id)
        tool.process_request(args.submission_id, payload)

