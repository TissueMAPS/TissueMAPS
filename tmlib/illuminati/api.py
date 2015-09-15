# encoding: utf-8
import os
import sys
import re
from tmt.illuminati import segment
from tmt.illuminati.mosaic import Mosaic
from tmt.experiment import Experiment
from tmt.project import Project


class Illuminati(object):

    '''Illuminati API'''

    def __init__(self, project_dir, cfg):
        '''
        Initialize an instance of class Illuminati.

        Parameters
        ----------
        project_dir: str
            path to project folder
        cfg: dict
            configuration settings

        See also
        --------
        `tmt.config`_
        '''
        self.project_dir = os.path.abspath(project_dir)
        self.cfg = cfg

    def create_channel_layer(self, channel_nr, layer_name,
                             illum_correct=False, shift=False,
                             thresh=False, thresh_value=None,
                             thresh_percent=9.99, thresh_sample=10,
                             stitch_only=False, output_dir=None):
        '''
        Create 8bit greyscale JPEG zoomify pyramid layer of "channel" images.

        Parameters
        ----------
        channel_nr: int
            number of the channel
        layer_name: str
            name the layer should get
        illum_correct: bool, optional
            whether images should be corrected for illumination artifacts
            according to statistics pre-calculated with the `corilla` package
            (defaults to False)
        shift: bool, optional
            whether the layer should be shifted according to shifts values
            pre-calculated with with the `align` package (defaults to False)
        tresh: bool, optional
            whether images should be thresholded before rescaling
        thresh_value: int, optional
            a fixed value used as thresholding level
        tresh_percent: float, optional
            a percentile used as thresholding level (defaults to 9.99)
        thresh_sample: int, optional
            number of images that will be sampled to calculate the
            `thresh_percent` percentile if no `thresh_value` is provided
            (defaults to 10)
        stitch_only: bool, optional
            whether the stitched image should be saved and no pyramid should
            be created (defaults to False)
        output_dir: str, optional
            path to the output directory (overwrite configuration settings)

        See also
        --------
        `illuminati.mosaic.Mosaic`
        '''
        #######################################################################
        #                       CONFIGURATION HANDLING                        #
        #######################################################################

        project = Project(self.project_dir, self.cfg)
        experiment = Experiment(project.experiment_dir, self.cfg)
        files = [f for f in project.image_files if f.channel == channel_nr]

        print('ᐄ  CREATING CHANNEL LAYER')
        layer = Mosaic(files, self.cfg)

        #######################################################################
        #                           IMAGE LOADING                             #
        #######################################################################

        print '.. Loading files'
        layer.build_channel_grid()

        #######################################################################
        #                        OUTPUT PREPARATION                           #
        #######################################################################

        if not output_dir:
            output_dir = self.cfg['LAYERS_FOLDER_FORMAT'].format(
                                    experiment_dir=experiment.experiment_dir,
                                    sep=os.path.sep)

        if not self.args.layer_name:
            raise IOError('You need to provide the name of the layer.')
        output_dir = os.path.join(output_dir, layer_name)

        if not os.path.exists(output_dir):
            print '.. Creating output directory: "%s"' % output_dir
            os.makedirs(output_dir)

        #######################################################################
        #                       ILLUMINATION CORRECTING                       #
        #######################################################################

        if illum_correct:
            print 'ᐄ  CORRECTING IMAGES FOR ILLUMINATION'

            # retrieve illumination correction statistics
            channel_index = [i for i, s in enumerate(project.stats_files)
                             if s.channel == channel_nr][0]
            stats = project.stats_files[channel_index]

            layer.apply_illumination_correction_to_grid(stats)

        #######################################################################
        #                             STITCHING                               #
        #######################################################################

        print '.. Stitching files to mosaic image'
        layer.stitch_images()

        #######################################################################
        #                              SHIFTING                               #
        #######################################################################

        if shift:
            print 'ᐄ  SHIFTING MOSAIC IMAGE'
            cycles = experiment.subexperiments
            current_cycle = files[0].cycle

            layer.shift_stitched_image(cycles, current_cycle)

        #######################################################################
        #                            THRESHOLDING                             #
        #######################################################################

        if thresh:
            print 'ᐄ  THRESHOLDING MOSAIC IMAGE'
            if thresh_value:
                print '   ... Using provided threshold value'
            else:
                if thresh_sample > len(files):
                    thresh_sample = len(files)
                print('   ... Computing threshold value corresponding to the '
                      '%d\% percentile on %d sampled files'
                      % (thresh_percent, thresh_sample))

            layer.apply_threshold_to_stitched_image(
                        thresh_value=thresh_value,
                        thresh_sample=thresh_sample,
                        thresh_percent=thresh_percent
            )

        print '.. Rescaling mosaic image'
        layer.scale_stitched_image()

        #######################################################################
        #                            PYRAMIDIZING                             #
        #######################################################################

        if stitch_only:
            print('ᐄ  SAVING MOSAIC IMAGE')
            layer.save_stitched_image(output_dir)
            print '🍺  Done!'
            sys.exit(0)

        print '.. Creating pyramid from mosaic image'
        layer.create_pyramid(output_dir)

    def create_mask_layer(self, objects_name, layer_name,
                          mask='outline', global_ids=False,
                          shift=False, stitch_only=False, output_dir=None):
        '''
        Create 8bit binary JPEG zoomify pyramid layer of "mask" images.

        .. Note::

            If argument `global_ids` is set to True, a 16bit PNG pyramid layer
            will be created. Such layers are not indented for direct
            visualization in the browser!

        Parameters
        ----------
        objects_name: str
            name of the segmented objects
        layer_name: str
            name the layer should get
        mask: str, optional
            either "area" or "outline", indicating whether the whole
            object area should be used or only the object outlines
            (defaults to "outline")
        shift: bool, optional
            whether the layer should be shifted according to shifts values
            pre-calculated with with the `align` package (defaults to False)
        global_ids: bool, optional
            whether a global ID mask should be created (defaults to False)
        stitch_only: bool, optional
            whether the stitched image should be saved and no pyramid should
            be created (defaults to False)
        output_dir: str, optional
            path to the output directory (overwrite configuration settings)

        See also
        --------
        `illuminati.mosaic.Mosaic`
        '''
        #######################################################################
        #                       CONFIGURATION HANDLING                        #
        #######################################################################

        project = Project(self.project_dir, self.cfg)
        experiment = Experiment(project.experiment_dir, self.cfg)

        files = [f for f in project.segmentation_files
                 if f.objects == objects_name]

        data_filename = experiment.data_filename

        if mask == 'outline':
            print('ᐄ  CREATING OUTLINE MASK LAYER')
        elif mask == 'area':
            print('ᐄ  CREATING AREA MASK LAYER')
        else:
            raise ValueError('Mask must either be "outline" or "area".')
        layer = Mosaic(files, self.cfg)

        #######################################################################
        #                          IMAGE LOADING                              #
        #######################################################################

        print '.. Loading files'
        layer.build_mask_grid(data_filename, mask=mask, global_ids=global_ids)

        #######################################################################
        #                       OUTPUT PREPARATION                            #
        #######################################################################

        if not output_dir:
            output_dir = self.cfg['LAYERS_FOLDER_FORMAT'].format(
                                    experiment_dir=experiment.experiment_dir,
                                    sep=os.path.sep)
            if not self.args.layer_name:
                layer_name = objects_name
            output_dir = os.path.join(output_dir, layer_name)

        if global_ids:
            output_dir = self.cfg['ID_PYRAMIDS_FOLDER_FORMAT'].format(
                                    experiment_dir=experiment.experiment_dir,
                                    sep=os.path.sep)
            no_rescale = True
            png = True
        else:
            # TissueMAPS requires mask layer folders to end on "_Mask"
            if not re.search('_Mask$', output_dir):
                output_dir = '%s_Mask' % output_dir

        if not os.path.exists(output_dir):
            print '.. Creating output directory: "%s"' % output_dir
            os.makedirs(output_dir)

        #######################################################################
        #                             STITCHING                               #
        #######################################################################

        print '.. Stitching files to mosaic image'
        layer.stitch_images()

        #######################################################################
        #                              SHIFTING                               #
        #######################################################################

        if shift:
            print 'ᐄ  SHIFTING MOSAIC IMAGE'
            cycles = experiment.subexperiments
            current_cycle = files[0].cycle

            layer.shift_stitched_image(cycles, current_cycle)

        #######################################################################
        #                            PYRAMIDIZING                             #
        #######################################################################

        if stitch_only:
            print('ᐄ  SAVING MOSAIC IMAGE')
            layer.save_stitched_image(output_dir)
            print '🍺  Done!'
            sys.exit(0)

        print '.. Creating pyramid from mosaic image'
        if not no_rescale and not png:
            layer.create_pyramid(output_dir)
        else:
            # The stitched image wasn't rescaled and is still 16 bit.
            # In order to have the resulting pyramid be 16 bit as well, we have
            # do change the file format from JPEG to PNG.
            # Note that pyramids created in this manner shouldn't be visualized
            # directly in the browser since they will be coerced to 8 bit,
            # which will result in loss of information.
            layer.create_pyramid(output_dir, tile_file_extension='.png')

    def create_lut(self, objects_name, output_dir=None):
        '''
        Create ID lookup table. 

        Parameters
        ----------
        objects_name: str
            name of the segmented objects
        output_dir: str, optional
            path to the output directory (overwrite configuration settings)

        See also
        --------
        `illuminati.segment.create_and_save_lookup_tables`
        '''

        # TODO: create LUTs as HDF5 files

        #######################################################################
        #                       CONFIGURATION HANDLING                        #
        #######################################################################
        project = Project(self.project_dir, self.cfg)

        files = [f for f in project.segmentation_files
                 if f.objects == objects_name]

        files = [f.image for f in files]
        layer = Mosaic(files, self.cfg)

        experiment = Experiment(project.experiment_dir, self.cfg)
        data_filename = experiment.data_filename

        print('ᐄ  CREATING ID LOOKUP TABLES ')

        #######################################################################
        #                        OUTPUT PREPARATION                           #
        #######################################################################

        output_dir = self.cfg['ID_TABLES_FOLDER_FORMAT'].format(
                                    experiment_dir=experiment.experiment_dir,
                                    sep=os.path.sep)

        if not os.path.exists(output_dir):
            print '.. Creating output directory: "%s"' % output_dir
            os.makedirs(output_dir)

        #######################################################################
        #                             CREATE LUTS                             #
        #######################################################################

        segment.create_and_save_lookup_tables(layer.image_grid,
                                              data_filename, output_dir)

    @staticmethod
    def process_cli_commands(args, subparser):
        '''
        Initialize an instance of class Illuminati
        with parsed command line arguments.

        Parameters
        ----------
        args: argparse.Namespace
            arguments parsed by command line interface
        subparser: argparse.ArgumentParser
            method that should be invoked
        '''
        cli = Illuminati(args.project_dir, args.config)
        if subparser.prog == 'il channel':
            cli.create_channel_layer(args.channel_nr, args.layer_name,
                                     args.illum_correct, args.shift,
                                     args.thresh, args.thresh_value,
                                     args.thresh_percent, args.thresh_sample,
                                     args.stitch_only, args.output_dir)
        elif subparser.prog == 'il mask':
            cli.create_mask_layer(args.objects_name, args.layer_name,
                                  args.mask, args.global_ids, args.shift,
                                  args.stitch_only, args.output_dir)
        elif subparser.prog == 'il lut':
            cli.create_lut(args.objects_name, args.output_dir)
        else:
            subparser.print_help()
