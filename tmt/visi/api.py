import os
import tmt
from tmt.visi.stk import Stk
from tmt.visi.stk2png import Stk2png


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
        project = Stk(self.args.stk_folder, self.args.wildcards)

        print '. Creating output directories'
        project.create_output_dirs(self.args.output_folder_name,
                                   self.args.split_output)

        print '. Creating joblist'
        project.create_joblist(self.args.batch_size)

        print '. Writing joblist to file'
        project.write_joblist()

    def run(self):
        '''
        Run unpacking of stk files with optional renaming.
        '''
        project = Stk(self.args.stk_folder, self.args.wildcards)

        if self.args.job:
            print '. Reading joblist from file'
            joblist = project.read_joblist()

            print '. Processing job #%d' % self.args.job
            batch = joblist[self.args.job]
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

    @staticmethod
    def process_cli_commands(args, subparser):
        cli = Visi(args)
        if subparser.prog == 'visi run':
            cli.run()
        elif subparser.prog == 'visi joblist':
            cli.joblist()
        else:
            subparser.print_help()
