import os
import numpy as np
from shapely.geometry import box
from shapely.geometry.polygon import Polygon
from ..mosaic import Mosaic
from ..metadata import MosaicMetadata
from .. import imageutils
from ..image_reader import OpenslideImageReader
from ..errors import NotSupportedError


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

    def align(self, shift_descriptions):
        '''
        Align mosaic according to pre-calculated shift values.

        To this end, the information stored in shift descriptor files is used.
        These files contain the shift between each pair of images from the
        obj_meta and the reference cycle in x and y direction. For the global
        alignment we use the median of the individual shift values. Based on
        those values, the intersection of mosaic images from different cycles
        is computed and the respective area is extracted form each image.

        Parameters
        ----------
        shift_descriptions: List[List[ShiftDescription]]
            shift description for each image of different cycles

        Returns
        -------
        Vips.Image
            aligned mosaic image

        Warning
        -------
        The mosaic image might have different dimensions after alignment.
        '''
        cycle_nrs = [d[0].cycle for d in shift_descriptions]
        current_cycle_ix = cycle_nrs.index(self.metadata.cycle)

        # TODO: global shifts could already be stored upon shift calculation!
        x_shifts = list()
        y_shifts = list()
        for d in shift_descriptions:
            x_shifts.append(np.median([s.x_shift for s in d]))
            y_shifts.append(np.median([s.y_shift for s in d]))

        # Create a Shapely rectangle for each image
        boxes = [box(x, y, x + self.mosaic.width, y + self.mosaic.height)
                 for x, y in zip(x_shifts, y_shifts)]

        # Compute the intersection of all those rectangles
        intersection = reduce(Polygon.intersection, boxes)
        min_x, min_y, max_x, max_y = intersection.bounds

        # How much to cut from the left side and from the top
        this_box = boxes[current_cycle_ix].bounds
        offset_left = min_x - this_box[0]
        offset_top = min_y - this_box[1]

        # How large is the extracted area (dimensions of the intersection)
        intersection_width = max_x - min_x
        intersection_height = max_y - min_y

        aligned_mosaic = self.mosaic.extract_area(
            offset_left, offset_top, intersection_width, intersection_height)

        return aligned_mosaic

    def scale(self):
        '''
        Scale mosaic.

        Searches the image for the maximum and minimum value,
        then returns the image as unsigned 8-bit, scaled such that the maximum
        value is 255 and the minimum is zero.

        Returns
        -------
        Vips.Image
            scaled mosaic image

        Raises
        ------
        AttributeError
            when mosaic does not exist
        '''
        scaled_mosaic = self.mosaic.scale()
        return scaled_mosaic

    def create_pyramid(self, layer_dir):
        '''
        Create zoomify pyramid (8-bit grayscale JPEG images) of mosaic.

        Parameters
        ----------
        layer_dir: str
            path to the folder where pyramid should be saved

        Raises
        ------
        AttributeError
            when `name` is not set
        '''
        if not hasattr(self, 'name'):
            raise AttributeError('Attribute "name" not set.')
        pyramid_dir = os.path.join(layer_dir, self.name)
        self.mosaic.dzsave(pyramid_dir, layout='zoomify', suffix='.jpg[Q=100]')


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

    @staticmethod
    def create_from_files(self, cycle, channel, dx=0, dy=0, **kwargs):
        '''
        Load individual images and stitch them together.

        The following additional arguments can be set:
        * "stats": illumination statistics to correct images for
          illumination artifacts (*IllumstatsImages*)
        * "shifts": shift descriptions to align individual wells between
          different cycles (*List[List[ShiftDescription]]*)

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
        **kwargs: dict
            additional arguments as key-value pairs

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
        if isinstance(cycle, 'Slide'):
            layer = ChannelLayer._create_from_slide(
                        cycle, channel, kwargs['stats'], kwargs['shifts'])
        elif isinstance(cycle, 'WellPlate'):
            layer = ChannelLayer._create_from_wellplate(
                        cycle, channel, kwargs['stats'], kwargs['shifts'])
        return layer

    @staticmethod
    def _create_from_slide(slide, channel, dx, dy, stats, shifts):
        images = [im for im in slide.images
                  if im.metadata.channel == channel]
        layer_name = slide.layer_names[channel]
        mosaic = Mosaic.create_from_images(images, dx, dy, stats)
        metadata = MosaicMetadata.create_from_images(images, layer_name)
        layer = ChannelLayer(mosaic, metadata)

        if shifts:
            layer = layer.align(shifts)

        return layer

    @staticmethod
    def _build_plate_grid(wellplate):
        plate_cooridinates = wellplate.plate_cooridinates
        height, width = np.max(wellplate.dimensions, axis=0)
        plate_grid = np.empty((height, width))
        for i, c in enumerate(plate_cooridinates):
            plate_grid[c[0], c[1]] = wellplate.wells[i]
        return plate_grid

    @staticmethod
    def _create_from_wellplate(wellplate, channel, dx, dy, stats, shifts):
        # Determine the dimensions of each well from one well (they should all
        # have the same dimensions) in order to create spacer images, which can
        # be used to fill gaps in the well plate (i.e. empty wells) and to
        # visually separate wells from each other
        images = [img for img in wellplate.images
                  if img.metadata.channel == channel
                  and img.metadata.well == wellplate.wells[0]]
        layer_name = wellplate.layer_names[channel]
        mosaic = Mosaic.create_from_images(images, dx, dy, stats)
        column_spacer = imageutils.create_spacer_image(
                            mosaic.dimensions, mosaic.dtype, 'horizontal')
        row_spacer = imageutils.create_spacer_image(
                            mosaic.dimensions, mosaic.dtype, 'vertical')
        empty_well_spacer = imageutils.create_spacer_image(
                            mosaic.dimensions, mosaic.dtype)

        plate_grid = ChannelLayer._build_plate_grid(wellplate)
        rows = list()
        for i in xrange(plate_grid.shape[0]):
            current_row = list()
            for j in xrange(plate_grid.shape[1]):
                well = plate_grid[i, j]
                if not well:
                    # NOTE: An empty background image takes less space on disk.
                    #       Comparison: 8bit JPEG image with 100x100 pixels:
                    #       img = Vips.Image.black(100, 100)
                    #       img.write_to_file('', Q=75, optimize_coding=True)
                    #       => 357 bytes
                    #       img = Vips.Image.gaussnoise(100, 100).cast('uchar')
                    #       img.write_to_file('', Q=75, optimize_coding=True)
                    #       => 4300 bytes
                    current_row.append(empty_well_spacer)
                images = [img for img in wellplate.images
                          if img.metadata.channel == channel
                          and img.metadata.well == well]
                mosaic = Mosaic.create_from_images(images, dx, dy, stats)
                metadata = MosaicMetadata.create_from_images(images, layer_name)
                layer = ChannelLayer(mosaic, metadata)
                if shifts:
                    layer.align(shifts)
                current_row.append(layer.mosaic.array)
                if not j == plate_grid.shape[1]:
                    current_row.append(column_spacer)

            rows.append(reduce(lambda x, y: x.merge(y, 'horizontal', 0, 0),
                               current_row))
            if not i == plate_grid.shape[0]:
                rows.append(row_spacer)

        img = reduce(lambda x, y: x.merge(y, 'vertical', 0, 0), rows)
        mosaic = Mosaic(img)
        metadata = MosaicMetadata.create_from_images(images, layer_name)
        layer = ChannelLayer(mosaic, metadata)
        return layer

    def clip(self, thresh_value=None, thresh_percent=None):
        '''
        Clip (limit) the pixel values in the mosaic image.

        Given a threshold level, values above threshold are set
        to the threshold level.

        Parameters
        ----------
        thresh_value: int
            pixel value
        thresh_percent: int
            threshold above which there are `thresh_percent` pixel values

        Returns
        -------
        ChannelLayer
            clipped mosaic image
        '''
        if not thresh_value:
            thresh_value = self.mosaic.percent(thresh_percent)
        condition_image = self.mosaic > thresh_value
        clipped_mosaic = condition_image.ifthenelse(thresh_value, self.mosaic)
        return clipped_mosaic


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

# class MaskLayer(Layer):

#     '''
#     Class for a mask layer, i.e. a mosaic layer that can be displayed
#     in TissueMAPS as a mask (overlay ontop of grayscale or RGB).
#     '''

#     def __init__(self, mosaic, cycle_id, name):
#         '''
#         Initialize an instance of class MaskLayer.

#         Parameters
#         ----------
#         mosaic: Vips.Image
#             stitched mosaic image
#         cycle_id: int
#             identifier number of the corresponding cycle
#         '''
#         super(MaskLayer, self).__init__(mosaic, cycle_id)
#         self.mosaic = mosaic
#         self.cycle_id = cycle_id

#     @staticmethod
#     def create_from_image_files(image_files, metadata, dx=0, dy=0, **kwargs):
#         '''
#         Load individual images and stitch them together according to the grid
#         layout defined by `metadata`.

#         The following additional arguments can be set:

#         * "data_file": str - absolute path to the HDF5 data file
#         * "use_outlines": bool - whether only the outlines of objects should
#           be used

#         Parameters
#         ----------
#         image_files: List[str]
#             absolute paths to of the image files
#         metadata: List[dict]
#             metadata for each image in `image_files`
#         dx: int, optional
#             displacement in x direction
#         dy: int, optional
#             displacement in y direction
#         **kwargs: dict
#             additional arguments as key-value pairs

#         Returns
#         -------
#         MaskLayer
#             mosaic image

#         Note
#         ----
#         Mask layers are used in TissueMAPS to visualize the position of
#         segmented objects. In addition, these objects can be selected
#         (i.e. one can click on them) and use the corresponding measured
#         features for further analysis. There may be objects in the images,
#         that we don't want to display, either because there are no data points
#         for them available in the dataset (for example due to alignment)
#         or because they lie at the border of individual images, which
#         would result in incomplete and biased measurements for these objects.
#         Therefore, we remove these objects from the images before stitching,
#         i.e. we set the corresponding pixel values to zero.

#         To this end, certain measurements are required for the objects, such
#         as their ids and their hierarchical relation to other types of objects,
#         and these measurements are retrieved from a pre-generated dataset
#         (stored in HDF5 format).

#         Note that removal of objects is based on the parent objects (e.g. cells)
#         and that all children objects (e.g. nuclei) are removed, too.

#         See also
#         --------
#         `dafu`_
#         '''
#         grid = MaskLayer._build_grid(image_files, metadata)
#         obj_name = metadata[0].objects.lower()
#         # Get ids for current objects from dataset (pandas data frames)
#         obj, parent = dafu.utils.extract_ids(kwargs['data_file'], obj_name)
#         with VipsImageReader() as reader:
#             rows = list()
#             for i in xrange(grid.shape[0]):
#                 current_row = list()
#                 for j in xrange(grid.shape[1]):
#                     # Objects without data points
#                     current_metadata = [m for m in metadata
#                                         if m.filename == grid[i, j]]
#                     site = current_metadata.site
#                     ids_image = obj.ids
#                     ids_data = np.unique(obj['ID_parent'][obj.ID_site == site])
#                     ids_nodata = [o for o in ids_data if o not in ids_image]
#                     # Border objects
#                     ids_border = parent['ID_object'][(parent.IX_border > 0) &
#                                                      (parent.ID_site == site)]
#                     ids_border = ids_border.tolist()
#                     ids_remove = ids_border + ids_nodata
#                     img = LabelImage(reader.read_image(grid[i, j]))
#                     img = img.remove_objects(ids_remove)
#                     if kwargs['use_outlines']:
#                         img = img.outlines
#                     current_row.append(img.pixels.array > 0)  # work with binary image
#                 rows.append(reduce(lambda x, y: x.merge(y, 'horizontal',
#                             dx, 0), current_row))
#         mosaic = reduce(lambda x, y: x.merge(y, 'vertical', 0, dy), rows)
#         layer = MaskLayer(mosaic)
#         return layer


# class LabelLayer(Layer):

#     '''
#     Class for a label layer, i.e. a labeled mask layer that encodes the
#     global unique ids of objects (connected components). It is used in
#     TissueMAPS to map pixel positions to objects ids.
#     '''

#     def __init__(self, mosaic, cycle_id):
#         '''
#         Initialize an instance of class LabelLayer.

#         Parameters
#         ----------
#         mosaic: Vips.Image
#             stitched mosaic image
#         cycle_id: int
#             identifier number of the corresponding cycle
#         '''
#         super(LabelLayer, self).__init__(mosaic, cycle_id)
#         self.mosaic = mosaic
#         self.cycle_id = cycle_id

#     def create_from_image_files(image_files, metadata, dx=0, dy=0, **kwargs):
#         '''
#         Load individual images and stitch them together according to the grid
#         layout defined by `metadata`.

#         Parameters
#         ----------
#         image_files: List[str]
#             absolute paths to of the image files
#         metadata: List[dict]
#             metadata for each image in `image_files`
#         dx: int, optional
#             displacement in x direction
#         dy: int, optional
#             displacement in y direction
#         **kwargs: dict
#             additional arguments as key-value pairs

#         Returns
#         -------
#         LabelLayer
#             stitched mosaic image

#         Note
#         ----
#         Label layers are used in TissueMAPS to visualize measured features or
#         analysis results on the segmented objects by dynamically colorizing
#         them according the calculated values.
#         To this end, the pixel belonging to each object must be identifiable
#         by a unique value. This global id is encoded by three digits,
#         which allows 3^(2^16) different objects to be encoded in a 16-bit RGB
#         image.

#         See also
#         --------
#         `illuminati.segment.local_to_global_ids_vips`_
#         '''
#         grid = LabelLayer._build_grid(image_files, metadata)
#         max_id = 0
#         with VipsImageReader() as reader:
#             rows = list()
#             for i in xrange(grid.shape[0]):
#                 current_row = list()
#                 for j in xrange(grid.shape[1]):
#                     img = LabelImage.create(
#                             image=reader.read(grid[i, j]['image']),
#                             metadata=grid[i, j]['metadata'])
#                     img, max_id = img.local_to_global_ids(max_id)
#                     max_id += 1
#                     if kwargs['use_outlines']:
#                         img = img.outlines
#                     current_row.append(img.pixels.array)
#                 rows.append(reduce(lambda x, y: x.merge(y, 'horizontal',
#                             dx, 0), current_row))
#         mosaic = reduce(lambda x, y: x.merge(y, 'vertical', 0, dy), rows)
#         layer = LabelLayer(mosaic)
#         return layer

#     def create_pyramid(self, layer_dir):
#         '''
#         Create zoomify pyramid (16-bit RGB PNG images) of mosaic.

#         Parameters
#         ----------
#         layer_dir: str
#             absolute path to the directory where pyramid should be saved

#         Raises
#         ------
#         AttributeError
#             when `name` is not set
#         '''
#         if not hasattr(self, 'name'):
#             raise AttributeError('Attribute "name" not set.')
#         pyramid_dir = os.path.join(layer_dir, self.name)
#         self.mosaic.dzsave(pyramid_dir, layout='zoomify', suffix='.png')

#     def scale(self):
#         '''
#         Raises
#         ------
#         AttributeError
#             label layers should not be rescaled to 8-bit
#         '''
#             raise AttributeError('"LabelLayers" object has no method "scale"')
