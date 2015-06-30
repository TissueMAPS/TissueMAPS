import os
import numpy as np
import tmt
import re
import h5py
import tmt.imageutil
from tmt.project import Project
from tmt.cluster import Cluster
from tmt.corilla.stats import OnlineStatistics


class Corilla(object):
    '''
    Class for corilla interface.
    '''

    def __init__(self, args):
        '''
        Initialize Corilla class.

        Parameters
        ----------
        args: Namespace
            arguments
        '''
        self.args = args
        self.args.project_dir = os.path.abspath(args.project_dir)

    def run(self):
        '''
        Run calculation of online statistics and write results to HDF5 file.
        '''
        self.args.config['USE_VIPS_LIBRARY'] = False  # TODO: Vips
        project = Project(self.args.project_dir, self.args.config)

        if not os.path.exists(project.stats_dir):
            print 'Creating output directory: %s' % project.stats_dir
            os.mkdir(project.stats_dir)

        channels = np.unique([i.channel for i in project.image_files])
        print 'Found %d channels' % len(channels)
        if self.args.channel:
            print 'Process only images of channel #%d' % self.args.channel
            channels = [c for c in channels if c == self.args.channel]
        for c in channels:
            print '\n. Calculating statistics for images of channel #%d' % c
            images = [i for i in project.image_files if i.channel == c]

            dims = images[0].dimensions
            stats = OnlineStatistics(dims)
            for im in images:
                print('.. Updating statistics with "%s"'
                      % os.path.basename(im.filename))
                stats.update(im.image)

            stats_filename = tmt.config['STATS_FILE_FORMAT'].format(channel=c)
            stats_filename = os.path.join(project.stats_dir, stats_filename)
            print '. Writing statistics to HDF5 file: "%s"' % stats_filename

            f = h5py.File(stats_filename, 'w')
            f.create_dataset('/stat_values/mean', data=stats.mean)
            f.create_dataset('/stat_values/std', data=stats.std)
            f.close()

    def apply(self):
        '''
        Apply calculated statistics in order to correct illumination artifacts.
        '''
        project = Project(self.args.project_dir, self.args.config)
        channels = np.unique([i.channel for i in project.image_files])
        print 'Found %d channels' % len(channels)
        if self.args.channels:
            channels = [c for c in channels if c in self.args.channels]
        for c in channels:
            print '\n. Correct images of channel #%d' % c
            if self.args.sites:
                images = [i for i in project.image_files
                          if i.channel == c and i.site in self.args.sites]
            else:
                images = [i for i in project.image_files if i.channel == c]
            # apply illumination correction
            stats = [f for f in project.stats_files if f.channel == c][0]
            for im in images:
                print '.. Process site #%d' % im.site
                im_corrected = stats.correct(im.image)
                suffix = os.path.splitext(im.filename)[1]
                output_filename = re.sub(r'\%s$' % suffix,
                                         '_corrected%s' % suffix,
                                         im.filename)
                output_filename = os.path.basename(output_filename)
                output_filename = os.path.join(self.args.output_dir,
                                               output_filename)
                tmt.imageutil.save_image(im_corrected, output_filename)

    def submit(self):
        '''
        Submit jobs for shift calculation.

        In contrast to other routines, submission doesn't require joblist!
        '''
        project = Project(self.args.project_dir, self.args.config)
        channels = np.unique([i.channel for i in project.image_files])
        print 'Found %d channels' % len(channels)

        if not os.path.exists(project.stats_dir):
            print 'Creating output directory: %s' % project.stats_dir
            os.mkdir(project.stats_dir)

        lsf_dir = os.path.join(project.experiment_dir, 'lsf')
        if not os.path.exists(lsf_dir):
            os.mkdir(lsf_dir)

        for c in channels:
            timestamp = tmt.cluster.create_timestamp()
            if not os.path.exists(lsf_dir):
                os.makedirs(lsf_dir)
            lsf = os.path.join(lsf_dir, 'corilla_%s_%s_C%.2d_%s.lsf'
                               % (project.experiment,
                                  project.subexperiment, c, timestamp))

            command = [
                'corilla', 'run', '--channel', str(c), self.args.project_dir
            ]

            print '. submitting calculation for channel #%d' % c
            job = Cluster(lsf)
            job.submit(command)

    @staticmethod
    def process_cli_commands(args, subparser):
        '''
        Initialize Corilla class with parsed command line arguments.

        Parameters
        ----------
        args: Namespace
            arguments parsed by command line interface
        subparser: argparse.ArgumentParser
        '''
        cli = Corilla(args)
        if subparser.prog == 'corilla run':
            cli.run()
        elif subparser.prog == 'corilla apply':
            cli.apply()
        elif subparser.prog == 'corilla submit':
            cli.submit()
        else:
            subparser.print_help()
