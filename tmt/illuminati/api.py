# encoding: utf-8
import os
import sys
import tmt
import glob
from tmt.illuminati import segment
from tmt.illuminati.mosaic import Mosaic
from tmt.experiment import Experiment
from tmt.project import Project
from tmt.image import IntensityImage, MaskImage


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

    def run(self):
        '''
        Run pyramid creation.

        Raises
        ------
        IOError
            when no files are found that match globbing pattern
        '''
        #######################################################################
        #                           LOADING IMAGES                            #
        #######################################################################

        project = Project(self.args.project_dir, self.args.config)
        files = glob.glob(os.path.join(project.image_dir,
                                       self.args.wildcards))

        if self.args.area_mask or self.args.outline_mask or self.args.id_luts:
            files = glob.glob(os.path.join(project.segmentation_dir,
                                           self.args.wildcards))
            if not files:
                raise IOError('No files were found in "%s" that match '
                              'provided pattern "%s"'
                              % (project.segmentation_dir,
                                 self.args.wildcards))
            images = [MaskImage(f, self.args.config) for f in files]
            # TODO: handle id_luts with Vips
        else:
            files = glob.glob(os.path.join(project.image_dir,
                                           self.args.wildcards))
            if not files:
                raise IOError('No files were found in "%s" that match '
                              'provided pattern "%s"'
                              % (project.image_dir,
                                 self.args.wildcards))
            images = [IntensityImage(f, self.args.config) for f in files]

        experiment = Experiment(project.experiment_dir, self.args.config)
        cycles = experiment.subexperiments
        current_cycle = images[0].cycle
        data_filename = experiment.data_filename

        if self.args.thresh_sample > len(images):
            self.args.thresh_sample = len(images)

        layer = Mosaic(images, self.args.config)

        if self.args.id_luts:
            print('ᐄ  CREATING ID LOOKUP TABLES ')
            segment.create_and_save_lookup_tables(layer.image_grid,
                                                  data_filename,
                                                  self.args.output_dir)
            print '🍺  Done!'
            sys.exit(0)

        # Create a vips image for each file
        print '.. Loading images'
        if self.args.outline_mask or self.args.area_mask:
            if self.args.outline_mask:
                print('ᐄ  CREATING OUTLINE MASKS')
                layer.build_mask_grid(data_filename, mask='outline',
                                      global_ids=self.args.make_global_ids)
            elif self.args.area_mask:
                print('ᐄ  CREATING AREA MASKS')
                layer.build_mask_grid(data_filename, mask='area',
                                      global_ids=self.args.make_global_ids)
        else:
            layer.build_channel_grid()

        #######################################################################
        #                       ILLUMINATION CORRECTING                       #
        #######################################################################

        if self.args.illum_correct:
            print 'ᐄ  CORRECTING IMAGES FOR ILLUMINATION'

            # retrieve illumination correction statistics
            channel_index = [i for i, s in enumerate(project.stats_files)
                             if s.channel == images[0].channel][0]
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
            layer.shift_stitched_image(cycles, current_cycle)

        #######################################################################
        #                            THRESHOLDING                             #
        #######################################################################

        if self.args.thresh:
            print 'ᐄ  THRESHOLDING MOSAIC IMAGE'
            if self.args.thresh_value:
                print '   ... Using provided threshold value'
            else:
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

    @staticmethod
    def process_cli_commands(args):
        '''
        Initialize Corilla class with parsed command line arguments.

        Parameters
        ----------
        args: argparse.Namespace
            arguments parsed by command line interface
        '''
        cli = Illuminati(args)
        cli.build()

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
        ui.run()

