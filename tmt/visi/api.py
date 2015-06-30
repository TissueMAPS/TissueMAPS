import os
import tmt
from tmt.visi.stk import Stk
from tmt.visi.stk2png import Stk2png
from tmt.cluster import Cluster


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
        project.create_joblist(self.args.batch_size)

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
            if self.args.rename:
                print '.. Rename images'
                process.rename_files()
            print '.. Unpack .stk files and convert them to .png images'
            process.unpack_images(output_dir=batch['output_dir'],
                                  keep_z=self.args.zstacks)
        else:

            print '. Creating output directories'
            project.create_output_dirs(self.args.output_folder_name,
                                       self.args.split_output)

            print '. Creating joblist'
            joblist = project.create_joblist(batch_size=1)

            for job, batch in enumerate(joblist):
                print '. Processing job #%d' % job
                process = Stk2png(batch['stk_files'], batch['nd_file'],
                                  self.args.config)
                if self.args.rename:
                    print '.. Rename images'
                    process.rename_files()
                print '.. Unpack .stk files and convert them to .png images'
                process.unpack_images(output_dir=batch['output_dir'],
                                      keep_z=self.args.zstacks)

    def submit(self):
        project = Stk(self.args.stk_folder, '*', config=self.args.config)
        joblist = project.read_joblist()

        lsf_dir = os.path.join(project.experiment_dir, 'lsf')
        if not os.path.exists(lsf_dir):
                os.mkdir(lsf_dir)

        for j in joblist:
            timestamp = tmt.cluster.create_timestamp()
            lsf = os.path.join(lsf_dir, 'visi_%s_%.5d_%s.lsf'
                               % (project.experiment, j['job_id'], timestamp))

            if self.args.config_file:
                command = [
                    'visi', 'run', '--job', str(j['job_id']), '--rename',
                    '--visi_config', self.args.config_file,
                    self.args.stk_folder
                ]
            else:
                command = [
                    'visi', 'run', '--job', str(j['job_id']), '--rename',
                    self.args.stk_folder
                ]

            print '. submitting job #%d' % j['job_id']
            job = Cluster(lsf)
            job.submit(command)

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
