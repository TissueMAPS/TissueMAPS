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

    def __init__(self, *args):
        self.args = args
        self.args.stk_folder = os.path.abspath(args.stk_folder)
        self._jobs = None
        # Create an instance of class Stk
        self.project = Stk(input_dir=self.args.stk_folder,
                           wildcards=self.args.wildcards,
                           config=self.args.config)

    def joblist(self):
        '''
        Create a list of jobs in YAML format for parallel computing.
        '''
        print '. Creating output directories'
        self.project.create_output_dirs(self.args.split_output)

        print '. Creating joblist'
        self.project.create_joblist(batch_size=self.args.batch_size,
                                    rename=self.args.rename)

        print '. Writing joblist to file'
        self.project.write_joblist()

    def run(self):
        '''
        Run unpacking of stk files with optional renaming.
        '''
        if self.args.job:

            job_ix = self.args.job-1  # job ids are one-based!

            print '. Reading joblist from file'
            joblist = self.project.read_joblist()

            print '. Processing job #%d' % self.args.job
            batch = joblist[job_ix]
            process = Stk2png(batch['stk_files'], batch['nd_file'],
                              self.args.config)
            print '.. Unpack .stk files and convert them to .png images'
            process.unpack_images(output_dir=batch['output_dir'],
                                  output_files=batch['png_files'],
                                  keep_z=self.args.zstacks)
        else:

            print '. Creating output directories'
            self.project.create_output_dirs(self.args.output_folder_name,
                                            self.args.split_output)

            print '. Creating joblist'
            joblist = self.project.create_joblist(batch_size=1,
                                                  rename=self.args.rename)

            for batch in joblist:
                print '. Processing job #%d' % batch['job_id']
                process = Stk2png(batch['stk_files'], batch['nd_file'],
                                  self.args.config)

                print '.. Unpack .stk files and convert them to .png images'
                process.unpack_images(output_dir=batch['output_dir'],
                                      output_files=batch['png_files'],
                                      keep_z=self.args.zstacks)

    def submit(self):
        '''
        Submit jobs to run in parallel on the cluster or in the cloud
        via GC3Pie.
        '''
        # Prepare log output directory
        log_dir = os.path.join(self.project.experiment_dir, 'log')
        if not os.path.exists(log_dir):
            os.mkdir(log_dir)

        # Create an `Engine` instance for running jobs in parallel
        e = gc3libs.create_engine()
        # Put all output files in the same directory
        e.retrieve_overwrites = True

        # Build parallel task collection
        self.build_jobs()

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

        # sequential task collection for "pipelines" of tasks with dependencies
        # jobs = gc3libs.workflow.SequentialTaskCollection(tasks=None)

    @property
    def jobs(self):
        '''
        Build a parallel task collection of "jobs" for GC3Pie.

        Returns
        -------
        jobs: gc3libs.workflow.ParallelTaskCollection
        '''
        if self._jobs is None:
            self._jobs = gc3libs.workflow.ParallelTaskCollection(
                            jobname='visi_%s_jobs' % self.project.experiment
            )
            joblist = self.project.read_joblist()
            for batch in joblist:

                timestamp = tmt.cluster.create_timestamp()
                log_file = 'visi_%s_job%.5d_%s.log' % (self.project.experiment,
                                                       batch['job_id'],
                                                       timestamp)

                if self.args.config_file:
                    command = [
                        'visi', 'run', '--job', str(batch['job_id']),
                        '--visi_config', self.args.config_file,
                        self.args.stk_folder
                    ]
                else:
                    command = [
                        'visi', 'run', '--job', str(batch['job_id']),
                        self.args.stk_folder
                    ]
                # Add individual task to collection
                app = gc3libs.Application(
                        arguments=command,
                        inputs=[batch['nd_file']] + batch['stk_files'],
                        outputs=batch['png_files'],
                        output_dir=batch['output_dir'],
                        jobname='visi_%s_%.5d' % (self.project.experiment,
                                                  batch['job_id']),
                        # write STDOUT and STDERR combined into one log file
                        stdout=log_file,
                        # activate the virtual environment "tmt"
                        application_name='tmt'
                )
                self._jobs.add(app)
        return self._jobs

    @staticmethod
    def process_cli_commands(args, subparser):
        cli = Visi(args)
        if subparser.prog == 'visi run':
            cli.run()
        elif subparser.prog == 'visi joblist':
            cli.joblist()
        elif subparser.prog == 'visi submit':
            cli.submit()
        else:
            subparser.print_help()
