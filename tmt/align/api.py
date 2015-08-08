import os
import glob
import h5py
import re
import sys
import numpy as np
import gc3libs
import gc3libs.workflow
from natsort import natsorted
import tmt
import imageutil
from align import registration as reg
from experiment import Experiment
import cluster
import utils


class Align(object):
    '''
    Class for alignment (registration) of images.
    '''

    def __init__(self, experiment_dir, cfg):
        '''
        Initialize an instance of class Align.

        Parameters
        ----------
        experiment_dir: str
            path to the experiment directory
        cfg: Dict[str, str]
            configuration settings

        See also
        --------
        `tmt.config`_
        '''
        self.experiment_dir = os.path.abspath(experiment_dir)
        self.cfg = cfg
        self.print_logo_and_prompt()
        self.cycles = Experiment(self.experiment_dir, self.cfg).subexperiments

    def print_logo_and_prompt(self):
        print tmt.align.logo % {'version': tmt.align.__version__}

    def joblist(self, batch_size, ref_channel, ref_cycle=None):
        '''
        Create a joblist in YAML format for parallel computing
        and write it to disk as `.jobs` file.

        Parameters
        ----------
        batch_size: int
            number of image files per job
        ref_channel: int
            number of the image channel that should be used as a reference for
            image registration
        ref_cycle: int
            number of the cycle that should be used as a reference for
            image registration
        '''
        print '. found %d cycles' % len(self.cycles)

        if ref_cycle:
            ref_cycle = ref_cycle - 1  # for zero-based indexing!
        else:
            # By default use last cycle as reference
            ref_cycle = len(self.cycles) - 1  # for zero-based indexing
        print '. reference cycle: %d' % (ref_cycle + 1)

        print '. reference channel: %d' % ref_channel

        shift = reg.Registration(self.cycles, ref_cycle, ref_channel)

        shift.create_output_dir()
        shift.create_joblist(batch_size)
        shift.write_joblist()

    def run(self, job_id=None, ref_channel=None, ref_cycle=None):
        '''
        Run shift and overhang calculation.

        Creates for each *batch* a `.registration` HDF5 file, where calculated
        shift and overhang values are stored.

        Parameters
        ----------
        job_id: int, optional
            one-based job index
        ref_channel: int, optional
            number of the image channel that should be used as a reference for
            image registration (required if `job_id` is not provided)
        ref_cycle: int, optional
            number of the cycle that should be used as a reference for
            image registration (required if `job_id` is not provided)

        See also
        --------
        `align.registration.calculate_shift`_
        `align.registration.calculate_overhang`_
        '''

        if job_id:

            job_ix = job_id-1  # job ids are one-based!

            shift = reg.Registration(self.cycles)
            print '. Reading joblist from file'
            joblist = shift.read_joblist()

            batch = joblist[job_ix]
            print '. Processing job #%d' % job_id
            reg.register_images(batch['acquisition_sites'],
                                batch['registration_files'],
                                batch['reference_files'],
                                os.path.join(batch['output_dir'],
                                             batch['output_file']))

        else:
            if not ref_channel or not ref_cycle:
                raise ValueError('If "job_id" is not specified, you need to '
                                 'provide the "ref_channel" and "ref_cycle" '
                                 'arguments')

            if ref_cycle:
                ref_cycle = ref_cycle - 1  # for zero-based indexing!
            else:
                # By default use last cycle as reference
                ref_cycle = len(self.cycles) - 1  # for zero-based indexing!
            print '. Reference cycle: %d' % (ref_cycle + 1)

            print '. Reference channel: %d' % ref_channel

            shift = reg.Registration(self.cycles, ref_cycle, ref_channel)
            shift.create_output_dir()
            joblist = shift.create_joblist(batch_size=1)

            for job, batch in enumerate(joblist):
                print '. Processing job #%d' % (job+1)
                reg.register_images(batch['acquisition_sites'],
                                    batch['registration_files'],
                                    batch['reference_files'],
                                    os.path.join(batch['output_dir'],
                                                 batch['output_file']))

    def fuse(self, max_shift, ref_cycle=None, segm_dir=None):
        '''
        Fuse shift calculations and create shift descriptor file.

        Reads the `.registration` HDF5 file created in the `run` step,
        concatenates the calculated shift values, calculates global overhang
        values and stores these values together with additional metainformation
        in YAML format.

        Parameters
        ----------
        max_shift: int
            shift value in pixels that is maximally tolerated (sites with
            larger shift values will be ignored)

        See also
        --------
        `align.registration.fuse_registration`_
        '''
        shift = reg.Registration(self.cycles)

        output_files = glob.glob(os.path.join(shift.registration_dir,
                                              '*.registration'))
        # Preallocate final output
        f = h5py.File(output_files[0], 'r')
        cycle_names = f.keys()
        f.close()

        descriptor = reg.fuse_registration(output_files, cycle_names)

        # Calculate overhang at each site
        print '. calculate overhang between sites'
        top, bottom, right, left, no_shift_index = \
            reg.calculate_overhang(descriptor, self.args.max_shift)

        # Write shiftDescriptor.json files
        for i, cycle_name in enumerate(cycle_names):
            print cycle_name
            current_cycle = [c for c in self.cycles
                             if c.name == cycle_name][0]
            aligncycles_dir = current_cycle.project.shift_dir
            if not os.path.exists(aligncycles_dir):
                os.mkdir(aligncycles_dir)
            descriptor_filename = self.cfg['SHIFT_FILE_FORMAT']
            descriptor_filename = os.path.join(aligncycles_dir,
                                               descriptor_filename)
            print '. create shift descriptor file: %s' % descriptor_filename

            for j in xrange(len(no_shift_index)):

                descriptor[i][j]['lower_overhang'] = bottom
                descriptor[i][j]['upper_overhang'] = top
                descriptor[i][j]['right_overhang'] = right
                descriptor[i][j]['left_overhang'] = left
                descriptor[i][j]['max_shift'] = max_shift
                descriptor[i][j]['dont_shift'] = no_shift_index[j]
                descriptor[i][j]['cycle'] = current_cycle.cycle

            # Sort entries according to filenames
            sorted_filenames = natsorted([(d['filename'], j)
                                          for j, d in enumerate(descriptor[i])])
            descriptor[i] = [descriptor[i][j] for f, j in sorted_filenames]

            utils.write_yaml(descriptor_filename, descriptor)

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
        cluster.submit_jobs_gc3pie(self.jobs)

    def build_jobs(self, shared_network=True):
        '''
        Build a GC3Pie parallel task collection of "jobs"
        as specified by the `joblist`.

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
        shift = reg.Registration(self.cycles)

        self.jobs = gc3libs.workflow.ParallelTaskCollection(
                        jobname='align_%s_jobs' % shift.experiment
        )
        # TODO: use a SequentialTaskCollection or StagedTaskCollection
        # and include the fusion step as an additional job

        try:
            joblist = shift.read_joblist()
        except OSError as e:
            sys.stderr.write(str(e))
            sys.stderr.write('Create a joblist first!\n'
                             'For help call "align joblist -h"')
            sys.exit(0)

        for j in joblist:

            jobname = 'align_%s_job-%.5d' % (shift.experiment, j['id'])
            timestamp = cluster.create_datetimestamp()
            log_file = '%s_%s.log' % (jobname, timestamp)
            # NOTE: There is a GDC3Pie bug that prevents the use of relative
            # paths for `stdout` and `stderr` to bundle log files
            # in a subdirectory of the `output_dir`

            command = [
                'align', 'run', '--job', str(j['id']),
                self.experiment_dir
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
                inputs = j['registration_files']
                inputs.extend(j['reference_files'])
                inputs.append(shift.joblist_file)
                outputs = j['output_file']

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

    def apply(self):
        '''
        Apply calculated shift and overhang values in order to align images.
        '''
        for c in self.cycles:
            print '\n. Processing images of cycle #%d' % c.cycle
            project = c.project
            channels = np.unique([i.channel for i in project.image_files])
            print '. Found %d channels' % len(channels)
            if self.args.channels:
                channels = [c for c in channels if c in self.args.channels]
            for c in channels:
                print '.. Align images of channel #%d' % c
                if self.args.sites:
                    images = [i for i in project.image_files
                              if i.channel == c and i.site in self.args.sites]
                else:
                    images = [i for i in project.image_files if i.channel == c]
                if not self.args.no_illcorr:
                    print '.. Correct images for illumination artifact'
                    stats = [f for f in project.stats_files
                             if f.channel == c][0]
                shift = project.shift_file
                for im in images:
                    img = im.image.copy()
                    if not self.args.no_illcorr:
                        img = stats.correct(img)
                    print '... Shift and crop "%s"' % im.name
                    aligned_im = shift.align(img, im.name)
                    suffix = os.path.splitext(im.filename)[1]
                    output_filename = re.sub(r'\%s$' % suffix,
                                             '_aligned_corrected%s' % suffix,
                                             im.filename)
                    output_filename = os.path.basename(output_filename)
                    output_filename = os.path.join(self.args.output_dir,
                                                   output_filename)
                    imageutil.save_image(aligned_im, output_filename)

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
        cli = Align(args.experiment_dir, args.config)
        if subparser.prog == 'align run':
            cli.run(args.job, args.ref_channel, args.ref_cycle)
        elif subparser.prog == 'align joblist':
            cli.joblist(args.batch_size, args.ref_channel, args.ref_cycle)
        elif subparser.prog == 'align fuse':
            cli.fuse(args.max_shift, args.ref_cycle, args.segm_dir)
        elif subparser.prog == 'align submit':
            cli.submit(args.shared_network)
        elif subparser.prog == 'align apply':
            cli.apply(args.shared_network)
        else:
            subparser.print_help()
