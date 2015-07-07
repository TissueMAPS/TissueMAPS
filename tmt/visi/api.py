import os
import tmt
import time
import gc3libs
import gc3libs.workflow
from tmt.visi.stk import Stk
from tmt.visi.stk2png import Stk2png
from tmt.cluster import Cluster

import logging
logger = logging.getLogger(__name__)
# gc3libs.configure_logger(level=logging.DEBUG)
gc3libs.configure_logger(level=logging.CRITICAL)


class Visi(object):
    '''
    Class for visi interface.
    '''

    def __init__(self, args):
        self.args = args
        self.args.stk_folder = os.path.abspath(args.stk_folder)

    def joblist(self):
        '''
        Create a list of jobs in YAML format for parallel computing.
        '''
        project = Stk(self.args.stk_folder, self.args.wildcards,
                      config=self.args.config)

        print '. Creating output directories'
        project.create_output_dirs(self.args.split_output)

        print '. Creating joblist'
        project.create_joblist(batch_size=self.args.batch_size,
                               rename=self.args.rename)

        print '. Writing joblist to file'
        project.write_joblist()

    def run(self):
        '''
        Run unpacking of stk files with optional renaming.
        '''
        project = Stk(self.args.stk_folder, self.args.wildcards,
                      config=self.args.config)

        if self.args.job:

            job_ix = self.args.job-1  # job ids are one-based!

            print '. Reading joblist from file'
            joblist = project.read_joblist()

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
            project.create_output_dirs(self.args.output_folder_name,
                                       self.args.split_output)

            print '. Creating joblist'
            joblist = project.create_joblist(batch_size=1,
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
        Submit jobs to run in parallel on a cluster.

        By default, `gc3pie` is used for job handling unless ``--brutus``
        argument is specified.
        '''
        project = Stk(self.args.stk_folder, '*', config=self.args.config)

        joblist = project.read_joblist()

        # Prepare for STDOUT log
        log_dir = os.path.join(project.experiment_dir, 'log')
        if not os.path.exists(log_dir):
            os.mkdir(log_dir)

        if not self.args.brutus:
            # Create an `Engine` instance for running jobs in parallel
            e = gc3libs.create_engine()
            # Put all output files in the same directory
            e.retrieve_overwrites = True
            # Create parallel task collection
            jobs = gc3libs.workflow.ParallelTaskCollection(
                    jobname='visi_%s_parallel_submission' % project.experiment
            )
            # jobs = gc3libs.workflow.SequentialTaskCollection(tasks=None)
        for batch in joblist:

            timestamp = tmt.cluster.create_timestamp()
            log_file = 'visi_%s_%.5d_%s.txt' % (project.experiment,
                                                batch['job_id'], timestamp)

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

            if self.args.brutus:
                print '. submitting job #%d' % batch['job_id']
                job = Cluster(log_file)
                job.submit(command)
            else:
                app = gc3libs.Application(
                    arguments=command,
                    inputs=[batch['nd_file']] + batch['stk_files'],
                    outputs=batch['png_files'],
                    output_dir=batch['output_dir'],
                    jobname='visi_%s_%.5d' % (project.experiment, batch['job_id']),
                    stdout=log_file.replace('.txt', '.out'),
                    stderr=log_file.replace('.txt', '.err')
                )
                jobs.add(app)

        if not self.args.brutus:
            # Add jobs tasks to engine instance
            e.add(jobs)

            print 'submit jobs'
            # Periodically check the status of the submitted jobs
            while jobs.execution.state != gc3libs.Run.State.TERMINATED:
                print "Jobs in status %s " % jobs.execution.state
                # `Engine.progress()` will do the GC3Pie magic:
                # submit new jobs, update status of submitted jobs, get
                # results of terminating jobs etc...
                e.progress()
                # Wait a few seconds...
                time.sleep(60)

            print 'Job is now terminated.'

            for task in jobs.iter_workflow():
                if(task.execution.returncode != 0
                        or task.execution.exitcode != 0):
                    print 'Job "%s" has failed!' % task.jobname
                    print task.stderr

        # sequential task collection for "pipelines" of tasks with dependencies

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
