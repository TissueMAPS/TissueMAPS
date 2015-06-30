# encoding: utf-8
import os
import sys
import tmt
import re
from tmt.illuminati import segment
from tmt.illuminati.mosaic import Mosaic
from tmt.experiment import Experiment
from tmt.project import Project


class IlluminatiArgs(object):

    def __init__(self):
        pass
        # TODO: parse arguments via defined attributes


class Illuminati(object):

    '''
    Class for illuminati interface.
    '''

    def __init__(self, args):
        '''
        Initialize Illuminati class.

        Parameters
        ----------
        args: argparse.Namespace or tmt.util.Namespacified
            arguments
        '''
        self.args = args
        self.args.project_dir = os.path.abspath(args.project_dir)

    def channel(self):
        '''
        Create pyramid for "channel" images.
        '''
        #######################################################################
        #                       CONFIGURATION HANDLING                        #
        #######################################################################

        project = Project(self.args.project_dir, self.args.config)

        files = [f for f in project.image_files
                 if f.channel == self.args.channel_nr]

        images = [f.image for f in files]
        layer = Mosaic(images, self.args.config)

        experiment = Experiment(project.experiment_dir, self.args.config)

        print('ᐄ  CREATING CHANNEL LAYER')

        #######################################################################
        #                           IMAGE LOADING                             #
        #######################################################################

        print '.. Loading images'
        layer.build_channel_grid()

        #######################################################################
        #                        OUTPUT PREPARATION                           #
        #######################################################################

        if not self.args.output_dir:
            self.args.output_dir = self.args.config['LAYERS_FOLDER_LOCATION'].format(
                                    experiment_dir=experiment.experiment_dir,
                                    sep=os.path.sep)
            if not self.args.layer_name:
                raise IOError('You need to provide the name of the layer.')
            self.args.output_dir = os.path.join(self.args.output_dir,
                                                self.args.layer_name)

        if not os.path.exists(self.args.output_dir):
            print '.. Creating output directory: "%s"' % self.args.output_dir
            os.makedirs(self.args.output_dir)

        #######################################################################
        #                       ILLUMINATION CORRECTING                       #
        #######################################################################

        if self.args.illum_correct:
            print 'ᐄ  CORRECTING IMAGES FOR ILLUMINATION'

            # retrieve illumination correction statistics
            channel_index = [i for i, s in enumerate(project.stats_files)
                             if s.channel == self.args.channel_nr][0]
            stats = project.stats_files[channel_index]

            layer.apply_illumination_correction_to_grid(stats)

        #######################################################################
        #                             STITCHING                               #
        #######################################################################

        print '.. Stitching images to mosaic image'

        layer.stitch_images()

        #######################################################################
        #                              SHIFTING                               #
        #######################################################################

        if self.args.shift:
            print 'ᐄ  SHIFTING MOSAIC IMAGE'
            cycles = experiment.subexperiments
            current_cycle = images[0].cycle

            layer.shift_stitched_image(cycles, current_cycle)

        #######################################################################
        #                            THRESHOLDING                             #
        #######################################################################

        if self.args.thresh:
            print 'ᐄ  THRESHOLDING MOSAIC IMAGE'
            if self.args.thresh_value:
                print '   ... Using provided threshold value'
            else:
                if self.args.thresh_sample > len(images):
                    self.args.thresh_sample = len(images)
                print('   ... Computing threshold value corresponding to the '
                      '%d\% percentile on %d sampled images'
                      % (self.args.thresh_percent, self.args.thresh_sample))

            layer.apply_threshold_to_stitched_image(
                        thresh_value=self.args.thresh_value,
                        thresh_sample=self.args.thresh_sample,
                        thresh_percent=self.args.thresh_percent
            )

        if not self.args.make_global_ids and not self.args.no_rescale:
            print '.. Rescaling mosaic image'
            layer.scale_stitched_image()

        #######################################################################
        #                            PYRAMIDIZING                             #
        #######################################################################

        if self.args.stitch_only:
            print('ᐄ  SAVING MOSAIC IMAGE')
            layer.save_stitched_image(self.args.output_dir)
            print '🍺  Done!'
            sys.exit(0)

        print '.. Creating pyramid from mosaic image'
        layer.create_pyramid(self.args.output_dir)

    def mask(self):
        '''
        Create pyramid of "mask" images.
        '''
        #######################################################################
        #                       CONFIGURATION HANDLING                        #
        #######################################################################

        project = Project(self.args.project_dir, self.args.config)

        files = [f for f in project.segmentation_files
                 if f.objects == self.args.objects_name]

        images = [f.image for f in files]
        layer = Mosaic(images, self.args.config)

        experiment = Experiment(project.experiment_dir, self.args.config)
        data_filename = experiment.data_filename

        if self.args.mask == 'outline':
            print('ᐄ  CREATING OUTLINE MASK LAYER')
        elif self.args.mask == 'area':
            print('ᐄ  CREATING AREA MASK LAYER')
        else:
            raise ValueError('Mask must either be "outline" or "area".')

        #######################################################################
        #                          IMAGE LOADING                              #
        #######################################################################

        print '.. Loading images'
        layer.build_mask_grid(data_filename, mask=self.args.mask,
                              global_ids=self.args.make_global_ids)

        #######################################################################
        #                       OUTPUT PREPARATION                            #
        #######################################################################

        if not self.args.output_dir:
            self.args.output_dir = self.args.config['LAYERS_FOLDER_LOCATION'].format(
                                    experiment_dir=experiment.experiment_dir,
                                    sep=os.path.sep)
            if not self.args.layer_name:
                raise IOError('You need to provide the name of the layer.')
            self.args.output_dir = os.path.join(self.args.output_dir,
                                                self.args.layer_name)

        if self.args.make_global_ids:
            self.args.output_dir = self.args.config['ID_PYRAMIDS_FOLDER_LOCATION'].format(
                                    experiment_dir=experiment.experiment_dir,
                                    sep=os.path.sep)
        else:
            # TissueMAPS requires mask layer folders to end on "_Mask"
            if not re.search('_Mask$', self.args.output_dir):
                self.args.output_dir = '%s_Mask' % self.args.output_dir

        if not os.path.exists(self.args.output_dir) and not self.args.id_luts:
            print '.. Creating output directory: "%s"' % self.args.output_dir
            os.makedirs(self.args.output_dir)

        #######################################################################
        #                             STITCHING                               #
        #######################################################################

        print '.. Stitching images to mosaic image'

        layer.stitch_images()

        #######################################################################
        #                              SHIFTING                               #
        #######################################################################

        if self.args.shift:
            print 'ᐄ  SHIFTING MOSAIC IMAGE'
            cycles = experiment.subexperiments
            current_cycle = images[0].cycle

            layer.shift_stitched_image(cycles, current_cycle)

        #######################################################################
        #                            PYRAMIDIZING                             #
        #######################################################################

        if self.args.stitch_only:
            print('ᐄ  SAVING MOSAIC IMAGE')
            layer.save_stitched_image(self.args.output_dir)
            print '🍺  Done!'
            sys.exit(0)

        print '.. Creating pyramid from mosaic image'
        if not self.args.no_rescale and not self.args.png:
            layer.create_pyramid(self.args.output_dir)
        else:
            # The stitched image wasn't rescaled and is still 16 bit.
            # In order to have the resulting pyramid be 16 bit as well, we have
            # do change the file format from JPEG to PNG.
            # Note that pyramids created in this manner shouldn't be visualized
            # directly in the browser since they will be coerced to 8 bit,
            # which will result in loss of information.
            layer.create_pyramid(self.args.output_dir,
                                 tile_file_extension='.png')

    def lut(self):
        '''
        Create ID lookup tables.
        '''

        # TODO: create LUTs as HDF5 files

        #######################################################################
        #                       CONFIGURATION HANDLING                        #
        #######################################################################
        project = Project(self.args.project_dir, self.args.config)

        files = [f for f in project.segmentation_files
                 if f.objects == self.args.objects_name]

        images = [f.image for f in files]
        layer = Mosaic(images, self.args.config)

        experiment = Experiment(project.experiment_dir, self.args.config)
        data_filename = experiment.data_filename

        print('ᐄ  CREATING ID LOOKUP TABLES ')

        #######################################################################
        #                        OUTPUT PREPARATION                           #
        #######################################################################

        self.args.output_dir = self.args.config['ID_TABLES_FOLDER_LOCATION'].format(
                                    experiment_dir=experiment.experiment_dir,
                                    sep=os.path.sep)

        if not os.path.exists(self.args.output_dir) and not self.args.id_luts:
            print '.. Creating output directory: "%s"' % self.args.output_dir
            os.makedirs(self.args.output_dir)

        #######################################################################
        #                             CREATE LUTS                             #
        #######################################################################

        segment.create_and_save_lookup_tables(layer.image_grid,
                                              data_filename,
                                              self.args.output_dir)

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
        cli = Illuminati(args)
        if subparser.prog == 'illuminati channel':
            cli.channel()
        elif subparser.prog == 'illuminati mask':
            cli.mask()
        elif subparser.prog == 'illuminati lut':
            cli.lut()
        else:
            subparser.print_help()

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
        ui = Illuminati(args)
