import os
import numpy as np
import tmt
import h5py
from tmt.project import Project
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
        project = Project(self.args.project_dir, self.args.config)

        channels = np.unique([i.channel for i in project.image_files])
        print 'Found %d channels' % len(channels)
        if self.args.channel:
            print 'Process only channel #%d' % self.arg.channel
            channels = [c for c in channels if c == self.args.channel]
        for c in channels:
            print '. Calculating statistics for channel #%d' % c
            images = [i for i in project.image_files if i.channel == c]

            dims = images[0].dimensions
            stats = OnlineStatistics(dims)
            for im in images:
                print im.filename
                stats.update(im.image,
                             log_transform=tmt.config['LOG_TRANSFORM_STATS'])

            stats_filename = tmt.config['STATS_FILE_FORMAT'].format(channel=c)
            stats_filename = os.path.join(project.stats_dir, stats_filename)
            print '. Writing statistics to HDF5 file: "%s"' % stats_filename

            f = h5py.File(stats_filename, 'w')
            f.create_dataset('/stat_values/mean', data=stats.mean)
            f.create_dataset('/stat_values/std', data=stats.std)
            f.close()

    @staticmethod
    def process_cli_commands(args):
        '''
        Initialize Corilla class with parsed command line arguments.

        Parameters
        ----------
        args: Namespace
            arguments parsed by command line interface
        '''
        cli = Corilla(args)
        cli.run()

    @staticmethod
    def process_ui_commands(args):
        '''
        Initialize Corilla class with parsed user interface arguments.

        Parameters
        ----------
        args: dict
            arguments parsed by user interface
        '''
        args = tmt.util.Namespacified(args)
        cli = Corilla(args)
        cli.run()
