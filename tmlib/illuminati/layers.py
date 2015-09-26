import os
import numpy as np
from ..mosaic import Mosaic
from ..metadata import MosaicMetadata
from .. import image_utils
from ..image_readers import OpenslideImageReader
from ..errors import NotSupportedError
from ..plates import Slide
from ..plates import WellPlate
import logging


class Layer(object):

    '''
    Abstract base class for a layer.

    A layer represents a 2D image (mosaic) that is stitched together from
    several individual images.
    '''

    def __init__(self, mosaic, metadata):
        '''
        Initialize an instance of class Layer.

        Parameters
        ----------
        mosaic: Mosaic
            stitched mosaic image
        metadata: MosaicMetadata
            metadata corresponding to the mosaic image
        '''
        self.mosaic = mosaic
        self.metadata = metadata

    def create_pyramid(self, pyramid_dir):
        '''
        Create zoomify pyramid (8-bit grayscale JPEG images) of mosaic.

        Parameters
        ----------
        pyramid_dir: str
            path to the folder where pyramid should be saved
        '''
        self.logger.info('create pyramid')
        self.mosaic.array.dzsave(
            pyramid_dir, layout='zoomify', suffix='.jpg[Q=100]')


class ChannelLayer(Layer):

    '''
    Class for a channel layer, i.e. a mosaic layer that can be displayed
    in TissueMAPS as a single grayscale channel or blended with other channels
    to RGB (additive color blending).
    '''

    def __init__(self, mosaic, metadata):
        '''
        Initialize an instance of class Layer.

        Parameters
        ----------
        mosaic: Mosaic
            stitched mosaic image
        metadata: MosaicMetadata
            metadata corresponding to the mosaic image
        '''
        super(ChannelLayer, self).__init__(mosaic, metadata)
        self.mosaic = mosaic
        self.metadata = metadata
        self.logger = logging.getLogger(self.__class__.__name__)

    @staticmethod
    def create_from_files(cycle, channel, dx=0, dy=0, stats=None, shift=None):
        '''
        Load individual images and stitch them together.

        Parameters
        ----------
        cycle: Slide or WellPlate
            cycle object
        channel: str
            name of the channel for which a layer should be created
        dx: int, optional
            displacement in x direction in pixels; useful when images are
            acquired with an overlap in x direction (negative integer value)
        dy: int, optional
            displacement in y direction in pixels; useful when images are
            acquired with an overlap in y direction (negative integer value)
        stats: IllumstatsImages, optional
            illumination statistics, when provided images are corrected for
            illumination artifacts
        shift: List[ShiftDescription], optional
            shift descriptions, when provided images are aligned between
            cycles

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
            when images are not all of the same cycle, channel, or well
        '''
        if isinstance(cycle, Slide):
            layer = ChannelLayer._create_from_slide(
                        cycle, channel, dx, dy, stats, shift)
        elif isinstance(cycle, WellPlate):
            layer = ChannelLayer._create_from_wellplate(
                        cycle, channel, dx, dy, stats, shift)
        return layer

    @staticmethod
    def _create_from_slide(slide, channel, dx, dy, stats, shift):
        images = [im for im in slide.images
                  if im.metadata.channel == channel]
        layer_name = slide.layer_names[channel]
        mosaic = Mosaic.create_from_images(images, dx, dy, stats, shift)
        metadata = MosaicMetadata.create_from_images(images, layer_name)
        layer = ChannelLayer(mosaic, metadata)

        return layer

    @staticmethod
    def _build_plate_grid(wellplate):
        plate_cooridinates = wellplate.plate_coordinates
        height, width = wellplate.dimensions  # one-based
        plate_grid = np.empty((height, width), dtype=object)
        for i, c in enumerate(plate_cooridinates):
            plate_grid[c[0], c[1]] = wellplate.wells[i]
        return plate_grid

    @staticmethod
    def _create_from_wellplate(wellplate, channel, dx, dy, stats, shift):
        # Determine the dimensions of each well from one well (they should all
        # have the same dimensions) in order to create spacer images, which can
        # be used to fill gaps in the well plate (i.e. empty wells) and to
        # visually separate wells from each other
        layer_name = wellplate.layer_names[channel]

        plate_grid = ChannelLayer._build_plate_grid(wellplate)

        # In case entire rows or columns are empty, we fill the gaps with
        # smaller spacer images to save disk space and computation time
        empty_rows = [
            all([g is None for g in plate_grid[i, :]])
            for i in xrange(plate_grid.shape[0])
        ]
        empty_columns = [
            all([g is None for g in plate_grid[:, j]])
            for j in xrange(plate_grid.shape[1])
        ]

        images = [img for img in wellplate.images
                  if img.metadata.channel == channel
                  and img.metadata.well == wellplate.wells[0]]
        mosaic = Mosaic.create_from_images(images, dx, dy, stats)
        gap_size = 750
        empty_well_spacer = image_utils.create_spacer_image(
                mosaic.dimensions[0], mosaic.dimensions[1],
                dtype=mosaic.dtype, bands=1)
        column_spacer = image_utils.create_spacer_image(
                mosaic.dimensions[0], gap_size,
                dtype=mosaic.dtype, bands=1)
        row_spacer = image_utils.create_spacer_image(
                gap_size,
                mosaic.dimensions[1]*plate_grid.shape[1] +
                column_spacer.width*(plate_grid.shape[1]-1),
                dtype=mosaic.dtype, bands=1)

        rows = list()
        for i in xrange(plate_grid.shape[0]):

            if empty_rows[i]:
                if i == 0:
                    rows.append(row_spacer)
                continue

            current_row = list()
            for j in xrange(plate_grid.shape[1]):

                if empty_columns[j]:
                    if j == 0:
                        current_row.append(column_spacer)
                    continue

                well = plate_grid[i, j]
                if not well:
                    current_row.append(empty_well_spacer)
                else:
                    images = [img for img in wellplate.images
                              if img.metadata.channel == channel
                              and img.metadata.well == well]
                    mosaic = Mosaic.create_from_images(
                                    images, dx, dy, stats, shift)
                    metadata = MosaicMetadata.create_from_images(
                                    images, layer_name)
                    layer = ChannelLayer(mosaic, metadata)
                    current_row.append(layer.mosaic.array)

                if not j == plate_grid.shape[1]:
                    current_row.append(column_spacer)

            rows.append(
                reduce(lambda x, y: x.join(y, 'horizontal'), current_row)
            )

            if not i == plate_grid.shape[0]:
                rows.append(row_spacer)

        img = reduce(lambda x, y: x.join(y, 'vertical'), rows)

        mosaic = Mosaic(img)
        metadata = MosaicMetadata.create_from_images(images, layer_name)
        layer = ChannelLayer(mosaic, metadata)
        return layer

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
            thresh_value = self.mosaic.array.percent(thresh_percent)
        lut = image_utils.create_thresholding_LUT(thresh_value)
        clipped_image = self.mosaic.array.maplut(lut)
        return ChannelLayer(Mosaic(clipped_image), self.metadata)


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
        `tmlib.image_readers.OpenslideImageReader`_
        '''
        with OpenslideImageReader() as reader:
            mosaic = reader.read(slide_file)
        name = os.path.splittext(os.path.basename(slide_file))[0]
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
