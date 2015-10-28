import os
import numpy as np
from . import utils
from . import image_utils
from .mosaic import Mosaic
from .metadata import MosaicMetadata
from .readers import OpenslideImageReader
from .errors import NotSupportedError
import logging

logger = logging.getLogger(__name__)


class ChannelLayer(object):

    '''
    Class for a channel layer, i.e. a mosaic layer that can be displayed
    in TissueMAPS as a single grayscale channel or blended with other channels
    to RGB (additive color blending).
    '''

    def __init__(self, mosaic, metadata):
        '''
        Initialize an instance of class ChannelLayer.

        Parameters
        ----------
        mosaic: tmlib.mosaic.Mosaic
            stitched mosaic image
        metadata: tmlib.metadata.MosaicMetadata
            metadata corresponding to the mosaic image

        Returns
        -------
        tmlib.layer.ChannelLayer
        '''
        self.mosaic = mosaic
        self.metadata = metadata
        self.logger = logging.getLogger(self.__class__.__name__)

    @staticmethod
    def create_from_files(experiment, tpoint_ix, channel_ix, zplane_ix,
                          dx=0, dy=0, illumcorr=False, shift=False):
        '''
        Load individual images and stitch them together.

        Parameters
        ----------
        experiment: tmlib.experiment.Experiment
            configured experiment object
        tpoint_ix: int
            time point (cycle) index
        channel_ix: int
            channel index
        zplane_ix: int
            z-plane index
        dx: int, optional
            displacement in x direction in pixels; useful when images are
            acquired with an overlap in x direction (negative integer value)
        dy: int, optional
            displacement in y direction in pixels; useful when images are
            acquired with an overlap in y direction (negative integer value)
        illumcorr: bool, optional
            whether images should be corrected for illumination artifacts
            (default: ``False``)
        shift: bool, optional
            whether images should be aligned between cycles
            (default: ``False``)

        Returns
        -------
        ChannelLayer
            stitched mosaic image

        Note
        ----
        In case `cycle` is of type `WellPlate`, an overview of the whole well
        plate is created. To this end, individual wells are stitched together
        and background pixels are inserted between wells to visually separate
        them from each other. Empty wells will also be filled with background.

        Raises
        ------
        MetadataError
            when images are not all of the same cycle, channel, plane, or well
        '''

        logger.info('stitch images to mosaic')
        layer_name = [
            lmd.name for lmd in experiment.layer_metadata
            if lmd.tpoint_ix == tpoint_ix
            and lmd.channel_ix == channel_ix
            and lmd.zplane_ix == zplane_ix
        ][0]
        # Plates are joined vertically:
        for p, plate in enumerate(experiment.plates):
            logger.info('stitching images of plate "%s" '
                        'for channel #%d and z-plane #%d',
                        plate.name, channel_ix, zplane_ix)
            plate_grid = ChannelLayer._build_plate_grid(plate)

            # In case entire rows or columns are empty, we fill the gaps with
            # smaller spacer images to save disk space and computation time
            nonempty_rows, nonempty_columns = np.where(plate_grid)

            # Determine the dimensions of wells based on one example well.
            # NOTE: all wells in an experiment must have the same dimensions!
            cycle = plate.cycles[tpoint_ix]
            md = cycle.image_metadata_table
            wells = np.unique(md['well_name'])
            index = np.where(
                        (md['tpoint_ix'] == tpoint_ix) &
                        (md['channel_ix'] == channel_ix) &
                        (md['zplane_ix'] == zplane_ix) &
                        (md['well_name'] == wells[0])
            )[0]
            images = [cycle.images[ix] for ix in index]

            mosaic = Mosaic.create_from_images(images, dx, dy, None, shift)
            gap_size = 500
            # Column spacer: insert between two wells in each row
            # (and instead of a well in case the whole column is empty
            # and lies between other nonempty columns)
            column_spacer = image_utils.create_spacer_image(
                    mosaic.dimensions[0], gap_size,
                    dtype=mosaic.dtype, bands=1)
            # Empty well spacer: insert instead of a well in case the well
            # is empty, but not the whole row or column is empty
            empty_well_spacer = image_utils.create_spacer_image(
                    mosaic.dimensions[0], mosaic.dimensions[1],
                    dtype=mosaic.dtype, bands=1)
            # Row spacer: insert between rows
            # (and instead of wells in case the whole row is empty and
            # the empty row lies between other nonempty rows)
            empty_columns_2fill = list(utils.missing_elements(
                                        list(set(nonempty_columns))))
            empty_rows_2fill = list(utils.missing_elements(
                                        list(set(nonempty_rows))))
            n_nonempty_cols = len(nonempty_columns)
            n_empty_cols_2fill = len(empty_columns_2fill)
            row_spacer = image_utils.create_spacer_image(
                    gap_size,
                    mosaic.dimensions[1]*n_nonempty_cols +
                    column_spacer.width*n_empty_cols_2fill +
                    column_spacer.width*(plate_grid.shape[1]+1),
                    dtype=mosaic.dtype, bands=1)

            if illumcorr:
                stats = cycle.illumstats_images[channel_ix]
            else:
                stats = None

            # Start each plate with a spacer
            layer_img = row_spacer

            for i in xrange(plate_grid.shape[0]):

                if i not in nonempty_rows:
                    if i in empty_rows_2fill:
                        # Fill empty row with spacer
                        # (if it lies between nonempty rows)
                        layer_img = layer_img.join(row_spacer, 'vertical')
                    continue

                for j in xrange(plate_grid.shape[1]):

                    if j == 0:
                        # Start each row with a spacer
                        row_img = column_spacer

                    if j not in nonempty_columns:
                        if j in empty_columns_2fill:
                            # Fill empty column with spacer
                            # (if it lies between nonempty columns)
                            row_img = row_img.join(column_spacer, 'horizontal')
                        continue

                    well = plate_grid[i, j]
                    if well is None:
                        # Fill empty well with spacer
                        row_img = row_img.join(empty_well_spacer, 'horizontal')
                    else:
                        index = np.where(
                                    (md['tpoint_ix'] == tpoint_ix) &
                                    (md['channel_ix'] == channel_ix) &
                                    (md['zplane_ix'] == zplane_ix) &
                                    (md['well_name'] == well)
                        )[0]
                        images = [cycle.images[ix] for ix in index]
                        mosaic = Mosaic.create_from_images(
                                        images, dx, dy, stats, shift)
                        row_img = row_img.join(mosaic.array, 'horizontal')

                    # Add small vertical gab between wells
                    row_img = row_img.join(column_spacer, 'horizontal')

                # Join rows together
                if p == 0 and i == 0:
                    layer_img = row_img
                else:
                    layer_img = layer_img.join(row_img, 'vertical')

                # Add small horizontal gab between rows of wells
                layer_img = layer_img.join(row_spacer, 'vertical')

            if len(experiment.plates) > 1:
                # Add an additional vertical gab between plates
                layer_img = layer_img.join(row_spacer, 'vertical')

        mosaic = Mosaic(layer_img)
        metadata = MosaicMetadata()
        metadata.name = layer_name
        metadata.tpoint_ix = tpoint_ix
        metadata.channel_ix = channel_ix
        metadata.zplane_ix = zplane_ix

        return ChannelLayer(mosaic, metadata)

    @staticmethod
    def _build_plate_grid(plate):
        plate_cooridinates = plate.well_coordinates
        height, width = plate.dimensions  # one-based
        plate_grid = np.empty((height, width), dtype=object)
        for i, c in enumerate(plate_cooridinates):
            plate_grid[c[0], c[1]] = plate.wells[i]
        return plate_grid

    def scale(self):
        '''
        Scale mosaic.

        Searches the image for the maximum and minimum value,
        then returns the image as unsigned 8-bit, scaled such that the maximum
        value is 255 and the minimum is zero.

        Returns
        -------
        ChannelLayer
            scaled mosaic image

        Raises
        ------
        AttributeError
            when mosaic does not exist
        '''
        scaled_image = self.mosaic.array.scale()
        return ChannelLayer(Mosaic(scaled_image), self.metadata)

    def clip(self, thresh_value=None, thresh_percent=None):
        '''
        Clip (limit) the pixel values in the mosaic image.

        Given a threshold level, values above threshold are set
        to the threshold level.

        Parameters
        ----------
        thresh_value: int
            value for the threshold level
        thresh_percent: int
            percentile to calculate the threshold level,
            e.g. if `thresh_percent` is 99.9% then 0.1% of pixels will lie
            above threshold

        Returns
        -------
        ChannelLayer
            clipped mosaic image
        '''
        if not thresh_value:
            # TODO: only consider non-empty wells
            thresh_value = self.mosaic.array.percent(thresh_percent)
        lut = image_utils.create_thresholding_LUT(thresh_value)
        clipped_image = self.mosaic.array.maplut(lut)
        return ChannelLayer(Mosaic(clipped_image), self.metadata)

    def create_pyramid(self, pyramid_dir):
        '''
        Create zoomify pyramid (8-bit grayscale JPEG images) of mosaic.

        Parameters
        ----------
        pyramid_dir: str
            path to the folder where pyramid should be saved
        '''
        self.mosaic.array.dzsave(
            pyramid_dir, layout='zoomify', suffix='.jpg[Q=100]')


class BrightfieldLayer(object):

    '''
    Class for a brightfield layer, i.e. a mosaic that can be displayed
    in TissueMAPS as RGB.

    Currently, brightfield mode is only available for virtual slide formats
    supported by the `Openslide <http://openslide.org/formats>`_ library.
    For compatibility with TissueMAPS the virtual slides are converted to
    *zoomify* format.
    '''

    def __init__(self, image_file):
        '''
        Initialize an instance of class BrightfieldLayer.

        Parameters
        ----------
        image_file: str
            absolute path to virtual slide image
        '''
        self.image_file = image_file

    @staticmethod
    def create_from_image_files(image_files, metadata, dx=0, dy=0, **kwargs):
        '''
        Not yet implemented.

        Raises
        ------
        NotSupportedError
        '''
        # TODO
        # with OpenslideMetadataReader() as reader:
        #     metadata = reader.read(slide_file)
        raise NotSupportedError('Not yet implemented')

    @staticmethod
    def create_from_slide_file(slide_file):
        '''
        Read highest-resolution level of a virtual slide.

        Parameter
        ---------
        slide_file: str
            absolute path to a virtual slide file

        Returns
        -------
        BrightfieldLayer
            mosaic image

        See also
        --------
        `tmlib.readers.OpenslideImageReader`_
        '''
        with OpenslideImageReader() as reader:
            mosaic = reader.read(slide_file)
        name = os.path.splitext(os.path.basename(slide_file))[0]
        return BrightfieldLayer(mosaic, cycle=None, name=name)

    def create_pyramid(self, layer_dir):
        '''
        Create zoomify pyramid (8-bit RGB JPEG images) of mosaic.

        Parameters
        ----------
        layer_dir: str
            absolute path to the directory where pyramid should be saved

        Raises
        ------
        AttributeError
            when `name` is not set
        '''
        if not hasattr(self, 'name'):
            raise AttributeError('Attribute "name" not set.')
        pyramid_dir = os.path.join(layer_dir, self.name)
        self.mosaic.dzsave(pyramid_dir, layout='zoomify', suffix='.jpg[Q=100]')

    def level_zero_tile_files(self):
        '''
        List the relative path within the pyramid directory to all tile images
        of level 0 (highest resolution level). 
        '''
        # TODO
        print('TODO')


class ObjectLayer(object):

    def __init__(self):
        pass
