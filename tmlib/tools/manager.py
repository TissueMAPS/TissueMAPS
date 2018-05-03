import os
import glob
import argparse
import socket
import logging
from whichcraft import which
from natsort import natsorted
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
from tmlib.log import configure_logging, map_logging_verbosity
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
        with tm.utils.ExperimentSession(self.experiment_id) as session:
            experiment = session.query(tm.Experiment).get(self.experiment_id)
            self._tools_location = experiment.tools_location

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
    def _batches_location(self):
        return os.path.join(self._tools_location, 'batches')

    @autocreate_directory_property
    def _log_location(self):
        return os.path.join(self._tools_location, 'logs')

    def _build_batch_filename_for_job(self, submission_id):
        filename = '%s_%d.json' % (self.__class__.__name__, submission_id)
        return os.path.join(self._batches_location, filename)

    def _build_command(self, submission_id):
        command = [
            'tm_tool',
            str(self.experiment_id),
            '--name', self.tool_name,
            '--submission_id', str(submission_id)
        ]
        command.extend(['-v' for x in range(self.verbosity)])
        logger.debug('submit tool request: %s', ' '.join(command))
        return command

    def create_job(self, submission_id, user_name, duration='06:00:00',
            # if all cores are used, we should allocate all available memory as well
            memory=cfg.resource.max_memory_per_core.amount(Memory.MB),
            cores=cfg.resource.max_cores_per_job):
        '''Creates a job for asynchroneous processing of a client tool request.

        Parameters
        ----------
        submission_id: int
            ID of the corresponding submission
        user_name: str
            name of the submitting user
        duration: str, optional
            computational time that should be allocated for the job
            in HH:MM:SS format (default: ``"06:00:00"``)
        memory: int, optional
            amount of memory in Megabyte that should be allocated for the job
            (defaults to
            :attr:`resource.max_memory_per_core <tmlib.config.LibraryConfig.resource>`)
        cores: int, optional
            number of CPU cores that should be allocated for the job
            (defaults to
            :attr:`resource.max_cores_per_job <tmlib.config.LibraryConfig.resource>`)

        Returns
        -------
        tmlib.tools.jobs.ToolJob
            tool job
        '''
        logger.info('create tool job for submission %d', submission_id)

        try:
            cores = int(cores)
        except (ValueError, TypeError) as err:
            raise TypeError(
                'Argument "cores" cannot be converted to type `int`: {err}'
                .format(err=err)
            )
        if not cores > 0:
            raise ValueError(
                'The value of "cores" must be positive.'
            )

        if cores > cfg.resource.max_cores_per_job:
            logger.warn(
                'requested cores exceed available cores per node:  %s',
                cfg.resource.max_cores_per_job
            )
            logger.warn(
                'lowering number of cores to %d (max available)',
                cfg.resource.max_cores_per_job
            )
            cores = cfg.resource.max_cores_per_job

        # FIXME: this needs to be revisited when GC3Pie issue #624 is fixed;
        # for the moment, see https://github.com/uzh/gc3pie/issues/624#issuecomment-328122862
        # as to why this is the right way to compute max memory
        max_memory_per_node = cfg.resource.max_memory_per_core.amount(Memory.MB)
        max_memory_per_core = max_memory_per_node / cfg.resource.max_cores_per_job
        if memory > max_memory_per_node:
            logger.warn(
                'requested memory exceeds available memory per node: %d MB',
                max_memory_per_node
            )
            logger.warn('lowering memory to %d MB', max_memory_per_node)
            memory = max_memory_per_node

        logger.debug('allocated time for job: %s', duration)
        logger.debug('allocated memory for job: %s MB', memory)
        logger.debug('allocated cores for job: %d', cores)
        job = ToolJob(
            tool_name=self.tool_name,
            arguments=self._build_command(submission_id),
            output_dir=self._log_location,
            submission_id=submission_id,
            user_name=user_name
        )
        job.requested_walltime = Duration(duration)
        job.requested_memory = Memory(memory, Memory.MB)
        job.requested_cores = cores
        return job

    def get_log_output(self, submission_id):
        '''Gets log output (standard output and error).

        Parameters
        ----------
        submission_id: int
            ID of the tool job
            :class:`Submission <tmlib.models.submission.Submission>`

        Returns
        -------
        Dict[str, str]
            "stdout" and "stderr" for the given job

        '''
        stdout_files = glob.glob(
            os.path.join(self._log_location, '*_%d_*.out' % submission_id)
        )
        stderr_files = glob.glob(
            os.path.join(self._log_location, '*_%d_*.err' % submission_id)
        )
        if not stdout_files or not stderr_files:
            raise IOError('No log files found for tool job #%d' % submission_id)
        # Take the most recent log files
        log = dict()
        with open(natsorted(stdout_files)[-1], 'r') as f:
            log['stdout'] = f.read()
        with open(natsorted(stderr_files)[-1], 'r') as f:
            log['stderr'] = f.read()
        return log

    def get_payload(self, submission_id):
        '''Get payload for tool request.

        Parameters
        ----------
        submission_id: int
            ID of the respective
            :class:`Submission <tmlib.models.submission.Submission>`

        Returns
        -------
        dict
            payload
        '''
        filename = self._build_batch_filename_for_job(submission_id)
        if not os.path.exists(filename):
            raise OSError(
                'Job description file does not exist: %s.' % filename
            )
        with JsonReader(filename) as f:
            return f.read()

    def store_payload(self, payload, submission_id):
        '''Persists payload for tool request on disk.

        Parameters
        ----------
        payload: dict
            tool job description in form of a mapping of key-value pairs
        submission_id: int
            ID of the corresponding
            :class:`Submission <tmlib.models.submission.Submission>`

        Raises
        ------
        TypeError
            when `payload` is not a mapping
        '''
        if not isinstance(payload, dict):
            raise TypeError('Playload must have type dict.')
        batch_file = self._build_batch_filename_for_job(submission_id)
        with JsonWriter(batch_file) as f:
            f.write(payload)

    @classmethod
    def _get_parser(cls):
        parser = argparse.ArgumentParser()
        parser.description = '''
            TissueMAPS command line interface for processing client tool
            requests.
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
            help='ID of the corresponding submission'
        )
        return parser

    @classmethod
    def __main__(cls):
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

        # Use multiple database connection simultaneouls per job.
        # The major bottleneck for tools is I/O, i.e. reading feature data from
        # the database and writing label values back.
        # Since we use a distributed database, we can speed up I/O using
        # multiple connections.
        tm.utils.set_pool_size(10)

        manager = cls(args.experiment_id, args.name, args.verbosity)
        manager._print_logo()
        payload = manager.get_payload(args.submission_id)
        tool_cls = get_tool_class(args.name)
        tool = tool_cls(args.experiment_id)
        tool.process_request(args.submission_id, payload)

        logger.info('done')
