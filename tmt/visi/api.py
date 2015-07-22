import os
import tmt
import sys
import gc3libs
import gc3libs.workflow
from tmt.visi.stk import Stk
from tmt.visi.stk2png import Stk2png
import tmt.cluster


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
        self.stk_folder = os.path.expandvars(stk_folder)
        self.stk_folder = os.path.expanduser(self.stk_folder)
        self.stk_folder = os.path.abspath(self.stk_folder)
        self.config = config
        # Create an instance of class Stk
        self.project = Stk(input_dir=self.stk_folder, wildcards=wildcards,
                           config=config)

    def joblist(self, batch_size, split_output=False, rename=False):
        '''
        Create a list of jobs in YAML format for parallel computing.

        Parameters
        ----------
        batch_size: int
            number of files per j job
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
            j = joblist[job_ix]
            process = Stk2png(j['stk_files'], j['nd_file'],
                              self.config)
            print '.. Unpack .stk files and convert them to .png images'
            process.unpack_images(output_dir=j['output_dir'],
                                  output_files=j['png_files'],
                                  keep_z=zstacks)
        else:

            print '. Creating output directories'
            self.project.create_output_dirs(self.args.output_folder_name,
                                            self.args.split_output)

            print '. Creating joblist'
            joblist = self.project.create_joblist(batch_size=1,
                                                  rename=rename)

            for j in joblist:
                print '. Processing job #%d' % j['id']
                process = Stk2png(j['stk_files'], j['nd_file'],
                                  self.config)

                print '.. Unpack .stk files and convert them to .png images'
                process.unpack_images(output_dir=j['output_dir'],
                                      output_files=j['png_files'],
                                      keep_z=zstacks)

    def submit(self, shared_network=True):
        '''
        Submit jobs to cluster or cloud to run in parallel. Requires prior
        creation of a `joblist`.

        Parameters
        ----------
        shared_network: bool, optional
            whether worker nodes have access to a shared network
            or filesystem (defaults to True)
        '''
        self.build_jobs(shared_network=shared_network)
        tmt.cluster.submit_jobs_gc3pie(self.jobs)

    def build_jobs(self, shared_network=True):
        '''
        Build a GC3Pie parallel task collection of "jobs".

        Parameters
        ----------
        shared_network: bool, optional
            whether worker nodes have access to a shared network
            or filesystem (defaults to True)

        Returns
        -------
        gc3libs.workflow.ParallelTaskCollection
            jobs
        '''
        self.jobs = gc3libs.workflow.ParallelTaskCollection(
                        jobname='visi_%s_jobs' % self.project.experiment
        )

        try:
            joblist = self.project.read_joblist()
        except OSError as e:
            print str(e)
            print('Create a joblist first!\nFor help call "visi joblist -h"')
            sys.exit(0)

        for j in joblist:

            jobname = 'visi_%s_job-%.5d' % (self.project.experiment, j['id'])
            timestamp = tmt.cluster.create_datetimestamp()
            log_file = '%s_%s.log' % (jobname, timestamp)
            # NOTE: There is a GDC3Pie bug that prevents the use of relative
            # paths for `stdout` and `stderr` to bundle log files
            # in a subdirectory of the `output_dir`

            command = [
                'visi', 'run', '--job', str(j['id']),
                self.stk_folder
            ]

            if shared_network:
                # This prevents files from being copied into ~/.gc3pie_jobs.
                # Instead they will be directly read from or written to disk,
                # which will dramatically speed up the processing time.
                # However, this only works if a shared network is available
                # on your resource!
                inputs = []
                outputs = []
            else:
                inputs = j['stk_files']
                inputs.append(j['nd_file'])
                inputs.append(self.project.joblist_file)
                outputs = j['png_files']

            # Add individual task to collection
            app = gc3libs.Application(
                    arguments=command,
                    inputs=inputs,
                    outputs=outputs,
                    output_dir=j['output_dir'],
                    jobname=jobname,
                    # write STDOUT and STDERR combined into a single log file
                    stdout=log_file,
                    join=True,
                    # activate the virtual environment
                    application_name='tmaps'
            )
            self.jobs.add(app)
        return self.jobs

    @staticmethod
    def process_cli_commands(args, subparser):
        '''
        Initializes an instance of class Visi with parsed command line
        arguments.

        For more info on the arguments of a particular subparser, call::

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
        cli = Visi(args.stk_folder, args.config)
        if subparser.prog == 'visi run':
            cli.run(args.zstacks, args.job, args.rename)
        elif subparser.prog == 'visi joblist':
            cli.joblist(args.batch_size, args.split_output, args.rename)
        elif subparser.prog == 'visi submit':
            cli.submit(args.shared_network)
        else:
            subparser.print_help()
