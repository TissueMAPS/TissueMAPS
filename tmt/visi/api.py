import os
import tmt
import time
import gc3libs
import gc3libs.workflow
from tmt.visi.stk import Stk
from tmt.visi.stk2png import Stk2png
import tmt.cluster

import logging
logger = logging.getLogger(__name__)
# gc3libs.configure_logger(level=logging.DEBUG)
gc3libs.configure_logger(level=logging.CRITICAL)


class Visi(object):
    '''
    Class for visi interface.
    '''

    def __init__(self, stk_folder, config, wildcards='*'):
        '''
        Initialize Visi class.

        Parameters
        ----------
        stk_folder: str
            path to the folder containing the .stk files
        config: Dict[str, str]
            configuration settings
        wildcards: str, optional
            globbing pattern to select subset of files in the `stk_folder`
        '''
        self.stk_folder = os.path.abspath(stk_folder)
        self.config = config
        # Create an instance of class Stk
        self.project = Stk(input_dir=stk_folder, wildcards=wildcards,
                           config=config)

    def joblist(self, batch_size, split_output=False, rename=False):
        '''
        Create a list of jobs in YAML format for parallel computing.

        Parameters
        ----------
        batch_size: int
            number of files per job
        split_output: bool, optional
            whether files belonging to different (sub)experiments, i.e.
            in case there are multiple .nd files in the input folder,
            should be split into separate output directories
            (defaults to False)
        rename: bool, optional
            whether files should be renamed according to configuration settings
            (defaults to False)
        '''
        print '. Creating output directories'
        self.project.create_output_dirs(split_output)

        print '. Creating joblist'
        self.project.create_joblist(batch_size, rename)

        print '. Writing joblist to file'
        self.project.write_joblist()

    def run(self, zstacks=False, job_id=None, rename=True):
        '''
        Run unpacking of stk files with optional renaming.

        Parameters
        ----------
        zstacks: bool, optional
            if True zstacks are saved as individual .png images,
            otherwise a maximum intensity projection is performed (default)
        job_id: int, optional
            id of the job that should be processed (defaults to None)
        rename: bool, optional
            whether files should be renamed according to configuration settings
            (defaults to False)
        '''
        if job_id:

            job_ix = job_id-1  # job ids are one-based!

            print '. Reading joblist from file'
            joblist = self.project.read_joblist()

            print '. Processing job #%d' % job_id
            batch = joblist[job_ix]
            process = Stk2png(batch['stk_files'], batch['nd_file'],
                              self.config)
            print '.. Unpack .stk files and convert them to .png images'
            process.unpack_images(output_dir=batch['output_dir'],
                                  output_files=batch['png_files'],
                                  keep_z=zstacks)
        else:

            print '. Creating output directories'
            self.project.create_output_dirs(self.args.output_folder_name,
                                            self.args.split_output)

            print '. Creating joblist'
            joblist = self.project.create_joblist(batch_size=1,
                                                  rename=rename)

            for batch in joblist:
                print '. Processing job #%d' % batch['job_id']
                process = Stk2png(batch['stk_files'], batch['nd_file'],
                                  self.config)

                print '.. Unpack .stk files and convert them to .png images'
                process.unpack_images(output_dir=batch['output_dir'],
                                      output_files=batch['png_files'],
                                      keep_z=zstacks)

    def submit(self):
        '''
        Submit jobs to cluster or cloud to run in parallel.

        You need to create a `joblist` and `build_jobs` first!
        '''
        # Create an `Engine` instance for running jobs in parallel
        e = gc3libs.create_engine()
        # Put all output files in the same directory
        e.retrieve_overwrites = True

        # Add tasks to engine instance
        e.add(self.jobs)

        # Periodically check the status of submitted jobs
        while self.jobs.execution.state != gc3libs.Run.State.TERMINATED:
            timestamp = tmt.cluster.create_timestamp(time_only=True)
            print "%s: Job status: %s " % (timestamp,
                                           self.jobs.execution.state)
            # `progess` will do the GC3Pie magic:
            # submit new jobs, update status of submitted jobs, get
            # results of terminating jobs etc...
            e.progress()
            time.sleep(10)

        for task in self.jobs.iter_workflow():
            if(task.execution.returncode != 0
                    or task.execution.exitcode != 0):
                print 'Job "%s" failed.' % task.jobname
                # resubmit?

        timestamp = tmt.cluster.create_timestamp(time_only=True)
        print '%s: All jobs terminated.' % timestamp

    def build_jobs(self, shared_network=False):
        '''
        Build a parallel task collection of "jobs" for GC3Pie.

        Parameters
        ----------
        shared_network: bool, optional
            whether worker nodes have access to a shared network
            or filesystem (defaults to False)

        Returns
        -------
        jobs: gc3libs.workflow.ParallelTaskCollection
        '''
        self.jobs = gc3libs.workflow.ParallelTaskCollection(
                        jobname='visi_%s_jobs' % self.project.experiment
        )
        try:
            joblist = self.project.read_joblist()
        except OSError:
            raise OSError('Create a joblist first!\n'
                          'For help call "visi joblist -h"')
        for batch in joblist:

            timestamp = tmt.cluster.create_timestamp()
            log_file = 'visi_%s_job%.5d_%s.log' % (self.project.experiment,
                                                   batch['job_id'],
                                                   timestamp)
            # NOTE: There is a GDC3Pie bug that prevents the use of relative
            # paths for `stdout` and `stderr` to bundle log files
            # in a subdirectory of the `output_dir`

            command = [
                'visi', 'run', '--job', str(batch['job_id']),
                self.stk_folder
            ]

            if self.args.shared_network:
                # This prevents that files are copied into ~/.gc3pie_jobs
                inputs = []
                outputs = []
            else:
                inputs = [batch['nd_file']] + batch['stk_files']
                outputs = batch['png_files']

            # Add individual task to collection
            app = gc3libs.Application(
                    arguments=command,
                    inputs=inputs,
                    outputs=outputs,
                    output_dir=batch['output_dir'],
                    jobname='visi_%s_%.5d' % (self.project.experiment,
                                              batch['job_id']),
                    # write STDOUT and STDERR combined into a log file
                    stdout=log_file,
                    # activate the virtual environment
                    application_name='tmt'
            )
            self.jobs.add(app)
        return self.jobs

    @staticmethod
    def process_cli_commands(args, subparser):
        '''
        Initializes an instance of class Visi with parsed command line
        arguments.

        For a list of arguments use the following command::

            visi <subparser_name> -h

        e.g.::

            visi run -h

        Parameters
        ----------
        args: argparse.Namespace
            arguments parsed by command line interface
        subparser: argparse.ArgumentParser
            subparser used in the command
        '''
        cli = Visi(args)
        if subparser.prog == 'visi run':
            cli.run(args.zstacks, args.job, args.rename)
        elif subparser.prog == 'visi joblist':
            cli.joblist(args.batch_size, args.split_output, args.rename)
        elif subparser.prog == 'visi submit':
            cli.build_jobs(args.shared_network)
            cli.submit()
        else:
            subparser.print_help()
