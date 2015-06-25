import os
import glob
import json
import h5py
import tmt
from tmt.align import registration as reg
from tmt.experiment import Experiment
from tmt.project import Project
from tmt.cluster import Cluster


class Align(object):
    '''
    Class for alignment of images based on registration.
    '''

    def __init__(self, args):
        '''
        Initialize Align class.

        Parameters
        ----------
        args: argparse.Namespace
            arguments
        '''
        self.args = args
        self.args.experiment_dir = os.path.abspath(args.experiment_dir)
        self.print_logo_and_prompt()

    def print_logo_and_prompt(self):
        print tmt.align.logo % {'version': tmt.align.__version__}

    def joblist(self):
        '''
        Create a joblist in YAML format for parallel computing.
        '''
        cycles = Experiment(self.args.experiment_dir,
                            self.args.config).subexperiments
        print '. found %d cycles' % len(cycles)

        if self.args.ref_cycle:
            ref_cycle = self.args.ref_cycle - 1  # for zero-based indexing!
        else:
            # By default use last cycle as reference
            ref_cycle = len(cycles) - 1  # for zero-based indexing
        print '. reference cycle: %d' % (ref_cycle + 1)

        ref_channel = self.args.ref_channel
        print '. reference channel: %d' % ref_channel

        shift = reg.Registration(cycles, ref_cycle, ref_channel)

        shift.create_output_dir()
        shift.create_joblist(self.args.batch_size)
        shift.write_joblist()

    def run(self):
        '''
        Run shift calculation.
        '''
        cycles = Experiment(self.args.experiment_dir,
                            self.args.config).subexperiments

        if self.args.job:

            job_ix = self.args.job-1  # job ids are one-based!

            shift = reg.Registration(cycles)
            print '. Reading joblist from file'
            joblist = shift.read_joblist()

            batch = joblist[job_ix]
            print '. Processing job #%d' % self.args.job
            reg.register_images(batch['registration_files'],
                                batch['reference_files'],
                                batch['output_file'])

        else:
            if self.args.ref_cycle:
                ref_cycle = self.args.ref_cycle - 1  # for zero-based indexing!
            else:
                # By default use last cycle as reference
                ref_cycle = len(cycles) - 1  # for zero-based indexing!
            print '. Reference cycle: %d' % (ref_cycle + 1)

            ref_channel = self.args.ref_channel
            print '. Reference channel: %d' % ref_channel

            shift = reg.Registration(cycles, ref_cycle, ref_channel)
            shift.create_output_dir()
            joblist = shift.create_joblist(batch_size=1)

            for job, batch in enumerate(joblist):
                print '. Processing job #%d' % (job+1)
                reg.register_images(batch['registration_files'],
                                    batch['reference_files'],
                                    batch['output_file'])

    def fuse(self):
        '''
        Fuse shift calculations and create shift descriptor JSON file.
        '''
        cycles = Experiment(self.args.experiment_dir,
                            self.args.config).subexperiments

        shift = reg.Registration(cycles)

        if self.args.ref_cycle:
            ref_cycle = self.args.ref_cycle
        else:
            # By default use last cycle as reference
            ref_cycle = len(cycles)
        print '. Reference cycle: %d' % ref_cycle
        ref_cycle_name = [c.name for c in cycles if c.cycle == ref_cycle][0]

        if self.args.segm_dir:
            segm_dir = self.args.segm_dir
        else:
            # relative path for Jterator projects
            segm_dir = self.args.config['SEGMENTATION_FOLDER_LOCATION'].format(
                                    experiment_dir='..%s..' % os.path.sep,
                                    sep=os.path.sep,
                                    subexperiment=ref_cycle_name)
        print '. Segmentation directory: %s' % segm_dir

        if self.args.segm_trunk:
            segm_trunk = self.args.segm_trunk
        else:
            exp_name = [c.experiment for c in cycles
                        if c.name == ref_cycle_name][0]
            segm_trunk = self.args.config['SUBEXPERIMENT_FILE_FORMAT'].format(
                                                        experiment=exp_name,
                                                        cycle=ref_cycle)
        print '. Segmentation trunk: %s' % segm_trunk

        output_files = glob.glob(os.path.join(shift.registration_dir,
                                              '*.output'))
        # Preallocate final output
        f = h5py.File(output_files[0], 'r')
        cycle_names = f.keys()
        f.close()

        descriptor = reg.fuse_registration(output_files, cycle_names)

        # Calculate overlap at each site
        print '. calculate overlap between sites'
        # top (t), bottom (b), right (r), left (l)
        t, b, r, l, no_shift_ix = reg.calculate_overlap(descriptor,
                                                        self.args.max_shift)

        no_shift_count = len(no_shift_ix)

        # Write shiftDescriptor.json files
        for i, cycle_name in enumerate(cycle_names):
            print cycle_name
            current_cycle = [c for c in cycles if c.name == cycle_name][0]
            aligncycles_dir = current_cycle.project.shift_dir
            if not os.path.exists(aligncycles_dir):
                os.mkdir(aligncycles_dir)
            descriptor_filename = self.args.config['SHIFT_FILE_FORMAT']
            descriptor_filename = os.path.join(aligncycles_dir,
                                               descriptor_filename)
            print '. create shift descriptor file: %s' % descriptor_filename

            descriptor[i]['lowerOverlap'] = b
            descriptor[i]['upperOverlap'] = t
            descriptor[i]['rightOverlap'] = r
            descriptor[i]['leftOverlap'] = l
            descriptor[i]['maxShift'] = self.args.max_shift
            descriptor[i]['noShiftIndex'] = no_shift_ix
            descriptor[i]['noShiftCount'] = no_shift_count
            descriptor[i]['segmentationDir'] = segm_dir
            descriptor[i]['segmentationFilenameTrunk'] = segm_trunk
            descriptor[i]['cycleNum'] = current_cycle.cycle

            with open(descriptor_filename, 'w') as outfile:
                outfile.write(json.dumps(descriptor[i],
                                         indent=4, sort_keys=True,
                                         separators=(',', ': ')))

    def submit(self):

        cycles = Experiment(self.args.experiment_dir,
                            self.args.config).subexperiments

        shift = reg.Registration(cycles)
        joblist = shift.read_joblist()

        lsf_dir = os.path.join(self.args.experiment_dir, 'lsf')
        if not os.path.exists(lsf_dir):
                os.mkdir(lsf_dir)

        for j in joblist:
            # build output filename
            timestamp = tmt.cluster.create_timestamp()
            lsf = os.path.join(lsf_dir, 'align_%s_%.5d_%s.lsf'
                               % (shift.experiment, j['job_id'], timestamp))
            if not os.path.exists(lsf):
                os.makedirs(lsf)

            # build command
            command = [
                'align', 'run', '--job', str(j['job_id']),
                self.args.experiment_dir
            ]

            print '. submitting job #%d' % j['job_id']
            job = Cluster(lsf)
            job.submit(command)

    def apply(self):
        # TODO
        pass

    @staticmethod
    def process_cli_commands(args, subparser):
        '''
        Initialize Corilla class with parsed command line arguments.

        Parameters
        ----------
        args: argparse.Namespace
            arguments parsed by command line interface
        subparser: argparse.ArgumentParser
        '''
        cli = Align(args)
        if subparser.prog == 'align run':
            cli.run()
        elif subparser.prog == 'align joblist':
            cli.joblist()
        elif subparser.prog == 'align fuse':
            cli.fuse()
        elif subparser.prog == 'align submit':
            cli.submit()
        elif subparser.prog == 'align apply':
            cli.apply()
        else:
            subparser.print_help()
