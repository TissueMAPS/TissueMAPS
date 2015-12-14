import os
import numpy as np
import pandas as pd
from collections import defaultdict
from skimage.measure import approximate_polygon
from gi.repository import Vips
from . import image_utils
from .mosaic import Mosaic
from .metadata import MosaicMetadata
from .readers import OpenslideImageReader
from .readers import DatasetReader
from .writers import DatasetWriter
from .errors import NotSupportedError
from .errors import PyramidCreationError
from .errors import DataError
import logging

logger = logging.getLogger(__name__)


class ChannelLayer(object):

    '''
    Channel layers are displayed as raster images. They are stored in form of
    `zoomify <http://www.zoomify.com/>`_ pyramids, which are represented on
    disk by JPEG files stored across multiple directories.
    '''

    def __init__(self, name, mosaic, metadata):
        '''
        Initialize an instance of class ChannelLayer.

        Parameters
        ----------
        name: str
            name of the layer
        mosaic: tmlib.mosaic.Mosaic
            stitched mosaic image
        metadata: tmlib.metadata.MosaicMetadata
            metadata corresponding to the mosaic image
        '''
        self.name = name
        self.mosaic = mosaic
        self.metadata = metadata

    @staticmethod
    def create(experiment, tpoint_ix, channel_ix, zplane_ix,
               clip_percentile=99.9, clip_value=None,
               displacement=0, illumcorr=False, align=False, spacer_size=500):
        '''
        Load individual images and stitch them together according to the
        metadata.

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
        clip_percentile: float, optional
            threshold percentile (default: ``99.9``)
        clip_value: int, optional
            fixed threshold value (default: ``None``)
        displacement: int, optional
            displacement in x, y direction in pixels; useful when images are
            acquired with an overlap direction (positive value; default: ``0``)
        illumcorr: bool, optional
            whether images should be corrected for illumination artifacts
            (default: ``False``)
        align: bool, optional
            whether images should be aligned between cycles
            (default: ``False``)
        spacer_size: int, optional
            number of pixels that should be introduced between wells
            (default: ``500``)

        Returns
        -------
        ChannelLayer
            stitched mosaic image

        Raises
        ------
        MetadataError
            when images are not all of the same cycle, channel, plane, or well

        Note
        ----
        In case `cycle` is of type `WellPlate`, an overview of the whole well
        plate is created. To this end, individual wells are stitched together
        and background pixels are inserted between wells to visually separate
        them from each other. Empty wells will also be filled with background.
        '''
        layer_name = experiment.layer_names[(tpoint_ix, channel_ix, zplane_ix)]
        layer_md = experiment.layer_metadata[layer_name]
        name = layer_md.name
        logger.info('create layer "%s"', name)

        # Set the size of the spacer. Note that this parameter has to be the
        # same for the creation of the corresponding object layers!
        logger.debug('spacer size: %d', spacer_size)

        nonempty_rows = defaultdict(list)
        nonempty_cols = defaultdict(list)
        for p, plate in enumerate(experiment.plates):
            plate_grid = plate.grid
            # In case entire rows or columns are empty, we fill the gaps with
            # smaller spacer images to save disk space and computation time
            # NOTE: all plate of an experiment must have the same layout, i.e.
            # the same number of wells and in case entire columns are
            # empty these must be same across all wells (e.g. for each plate
            # the outer rim of wells can be left out during image acquisition)
            nonempty_wells = np.where(plate_grid)
            nonempty_rows[tuple(np.unique(nonempty_wells[0]))].append(plate.name)
            nonempty_cols[tuple(np.unique(nonempty_wells[1]))].append(plate.name)

        if len(set([plate.n_wells for plate in experiment.plates])) > 1:
            raise PyramidCreationError('Layout of plates must be identical.')

        if len(nonempty_rows.keys()) > 1 or len(nonempty_cols.keys()) > 1:
            raise PyramidCreationError('Layout of plates must be identical.')

        nonempty_columns = nonempty_cols.keys()[0]
        nonempty_rows = nonempty_rows.keys()[0]

        # Determine the dimensions of wells based on one example well.
        # NOTE: all wells in an experiment must have the same dimensions!
        cycle = experiment.plates[0].cycles[tpoint_ix]
        md = cycle.image_metadata
        image = cycle.get_image_subset([0])[0]

        n_rows = np.max(md.well_position_y) + 1
        n_cols = np.max(md.well_position_x) + 1
        well_dimensions = (
            n_rows * image.pixels.dimensions[0] + displacement * (n_rows - 1),
            n_cols * image.pixels.dimensions[1] + displacement * (n_cols - 1)
        )
        # Empty well spacer: insert instead of a well in case the well
        # is empty, but not the whole row or column is empty
        logger.debug('create empty well spacer: %d x %d pixels',
                     well_dimensions[0], well_dimensions[1])
        empty_well_spacer = image_utils.create_spacer_image(
                well_dimensions[0], well_dimensions[1],
                dtype=image.pixels.dtype, bands=1)

        # Joined plates vertically
        thresholds = list()
        mosaics_images = list()
        for p, plate in enumerate(experiment.plates):

            logger.info('stitch images of plate "%s" '
                        'for channel #%d and z-plane #%d',
                        plate.name, channel_ix, zplane_ix)

            if illumcorr:
                stats = cycle.illumstats_images[channel_ix]
            else:
                stats = None

            overview = None
            for i in xrange(plate_grid.shape[0]):

                if i not in nonempty_rows:
                    # Skip empty rows
                    continue

                logger.debug('stitch images of row # %d', i)

                for j in xrange(plate_grid.shape[1]):

                    if j not in nonempty_columns:
                        # Skip empty columns
                        continue

                    well = plate_grid[i, j]
                    logger.debug('stitch images of well "%s"', well)

                    if well is None:
                        # Fill empty well with spacer
                        mosaics_images.append(empty_well_spacer)
                    else:
                        index = np.where(
                                    (md['tpoint_ix'] == tpoint_ix) &
                                    (md['channel_ix'] == channel_ix) &
                                    (md['zplane_ix'] == zplane_ix) &
                                    (md['well_name'] == well)
                        )[0]
                        images = cycle.get_image_subset(index)
                        mosaic = Mosaic.create(
                                    images, displacement, stats, align)
                        img = mosaic.array
                        mosaics_images.append(mosaic.array)
                        # Calculate clip threshold for a few sampled images
                        if clip_value is None:
                            n_images = len(images)
                            if n_images < 10:
                                n_samples = n_images
                            else:
                                n_samples = 10
                            samples = np.random.choice(
                                        range(n_images), size=n_samples,
                                        replace=False)
                            for s in samples:
                                img = images[s].pixels.array
                                thresh = img.percent(clip_percentile)
                                thresholds.append(thresh)

        overview = Vips.Image.arrayjoin(
                        mosaics_images,
                        across=len(nonempty_columns), shim=spacer_size)

        mosaic = Mosaic(overview)
        metadata = MosaicMetadata()
        metadata.tpoint_ix = tpoint_ix
        metadata.channel_ix = channel_ix
        metadata.zplane_ix = zplane_ix

        layer = ChannelLayer(name, mosaic, metadata)

        # Rescale images to 8-bit, limiting the range of intensity values for
        # visualization
        if clip_value is None:
            clip_value = int(np.median(thresholds))
        layer = layer.clip(max_value=clip_value)
        layer = layer.scale(max_value=clip_value)

        return layer

    def scale(self, max_value=65536):
        '''
        Scale the mosaic as unsigned 8-bit, such that `max_value` is 255.

        Parameters
        ----------
        max_value: int, optional
            maximum value (default: ``65536``)

        Returns
        -------
        ChannelLayer
            scaled mosaic image
        '''
        logger.info('rescale intensities between 0 and %d', max_value)
        mat = Vips.Image.new_from_array([[0, 0], [max_value, 255]])
        lut = mat.buildlut()
        scaled_image = self.mosaic.array.maplut(lut)
        return ChannelLayer(self.name, Mosaic(scaled_image), self.metadata)

    def clip(self, max_value=65536):
        '''
        Set values outside of the interval to the values of the interval edges,
        i.e. set values above `max_value` to `max_value` 

        Parameters
        ----------
        max_value: int, optional
            maximum value (default: ``65536``)

        Returns
        -------
        ChannelLayer
            clipped mosaic image
        '''
        logger.info('clip intensities above %d', max_value)
        identity = Vips.Image.identity(ushort=True)
        # Create lookup table
        condition = (identity > max_value)
        lut = condition.ifthenelse(max_value, identity)
        # Map the image through the lookup table
        clipped_image = self.mosaic.array.maplut(lut)
        return ChannelLayer(self.name, Mosaic(clipped_image), self.metadata)

    def save(self, directory):
        '''
        Create *zoomify* pyramid (8-bit grayscale JPEG images) of mosaic.

        Parameters
        ----------
        directory: str
            path to the folder where pyramid should be saved

        Note
        ----
        `directory` shouldn't exist, but will be created automatically

        See also
        --------
        :py:attribute:`tmlib.experiment.Experiment.layers_dir`
        '''
        self.mosaic.array.dzsave(
            directory, layout='zoomify', suffix='.jpg[Q=100]')


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
        #     metadata = data.read(slide_file)
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

    '''
    Object layers are displayed as vector graphics. The objects are represented
    by coordinates, which are stored in a HDF5 file.
    '''

    def __init__(self, name, coordinates):
        '''
        Initialize an object of class ObjectLayer.

        Parameters
        ----------
        name: str
            name of the layer
        coordinates: Dict[int, pandas.DataFrame]
            y, x coordinates of the outlines of each object
        '''
        self.name = name
        self.coordinates = coordinates

    @staticmethod
    def create(experiment, name, displacement=0, spacer_size=500):
        '''
        Create an object layer based on segmentations stored in data file.

        Parameters
        ----------
        experiment: tmlib.experiment.Experiment
            configured experiment object
        name: str
            name of the objects for which a layer should be created;
            a corresponding subgroup must exist in "/objects" within the data
            file
        displacement: int, optional
            displacement in x, y direction in pixels; useful when images are
            acquired with an overlap (positive value, default: ``0``)
        spacer_size: int, optional
            number of pixels that should be introduced between wells
            (default: ``500``)

        Warning
        -------
        Argument `spacer_size` must be the same as for the
        :py:class:`tmlib.layer.ChannelLayer`, otherwise objects will not
        align with the images.
        '''
        logger.info('create layer "%s"', name)

        filename = os.path.join(experiment.dir, experiment.data_file)
        segmentation_path = '/objects/%s/segmentation' % name
        with DatasetReader(filename) as data:
            if not data.exists(segmentation_path):
                raise DataError(
                        'The data file does\'t contain any segmentations: %s'
                        % segmentation_path)
            # Get the site indices of individual images.
            # (can be used to obtain the position of the image within the grid)
            unique_job_ids = map(int, data.list_groups('/metadata'))
            # Get the dimensions of the original, unaligned image
            image_dimensions = (
                data.read('/metadata/image_dimension_y', index=0),
                data.read('/metadata/image_dimension_x', index=0)
            )
            # Get the indices of objects at the border of images
            # (using the parent objects as references)
            if 'plate_name' in data.list_groups(segmentation_path):
                parent = data.read('%s/parent_name' % segmentation_path)
                parent_segmentation_path = '/objects/%s/segmentation' % parent
                border = data.read('%s/is_border' % parent_segmentation_path)
            else:
                border = data.read('%s/is_border' % segmentation_path)

            # Get the coordinates of object outlines within individual images.
            coords_y = data.read('%s/outlines/y' % segmentation_path)
            coords_x = data.read('%s/outlines/x' % segmentation_path)

            # A jterator job represents a unique image acquisition site.
            # We have to identify the position of each site within the overall
            # acquisition grid and update the outline coordinates accordingly,
            # i.e. translate site-specific coordinates into global ones.

            # Get the dimensions of wells from one example well. It's assumed
            # that all wells have the same dimensions!
            cycle = experiment.plates[0].cycles[0]
            md = cycle.image_metadata
            well_name = data.read('/metadata/well_name',
                                  index=unique_job_ids[0]-1)
            index = (
                        (md['tpoint_ix'] == 0) &
                        (md['channel_ix'] == 0) &
                        (md['zplane_ix'] == 0) &
                        (md['well_name'] == well_name)
            )
            # Determine the dimensions of a well in pixels, accounting for a
            # potential overlap of images.
            n_rows = np.max(md['well_position_y'][index]) + 1
            n_cols = np.max(md['well_position_x'][index]) + 1
            well_dimensions = (
                n_rows * image_dimensions[0] + displacement * (n_rows - 1),
                n_cols * image_dimensions[1] + displacement * (n_cols - 1)
            )

            # Plate dimensions are defined as number of pixels along each
            # axis of the plate. Note that empty rows and columns are also
            # filled with "spacers", which has to be considered as well.
            plate = experiment.plates[0]
            n_nonempty_rows = len(plate.nonempty_row_indices)
            n_nonempty_cols = len(plate.nonempty_column_indices)
            plate_y_dim = (
                n_nonempty_rows * well_dimensions[0] +
                # Spacer between wells
                (n_nonempty_rows - 1) * spacer_size
            )
            plate_x_dim = (
                n_nonempty_cols * well_dimensions[1] +
                # Spacer between wells
                (n_nonempty_cols - 1) * spacer_size
            )
            plate_dimensions = (plate_y_dim, plate_x_dim)

            plate_names = [p.name for p in experiment.plates]
            job_ids = data.read('%s/job_ids' % segmentation_path)
            global_coords = dict()
            for j in unique_job_ids:
                i = j - 1  # job ids are one-based
                plate_name = data.read('metadata/plate_name', index=i)
                plate_index = plate_names.index(plate_name)
                well_name = data.read('metadata/well_name', index=i)

                plate_coords = plate.map_well_id_to_coordinate(well_name)
                well_coords = (
                    data.read('metadata/well_position_y', index=i),
                    data.read('metadata/well_position_x', index=i)
                )

                # Images may be aligned and the resulting shift must be
                # considered.
                shift_offset_y = data.read('/metadata/shift_offset_y', index=i)
                shift_offset_x = data.read('metadata/shift_offset_x', index=i)

                n_prior_well_rows = plate.nonempty_row_indices.index(
                                            plate_coords[0])
                offset_y = (
                    # Images in the current well above the image
                    well_coords[0] * image_dimensions[0] +
                    # Potential overlap of images in y-direction
                    well_coords[0] * displacement +
                    # Wells in the current plate above the current well
                    n_prior_well_rows * well_dimensions[0] +
                    # Gap introduced between wells
                    # plate_coords[0] * spacer_size +
                    n_prior_well_rows * spacer_size +
                    # Potential shift of images downwards
                    shift_offset_y +
                    # Plates above the current plate
                    plate_index * plate_dimensions[0]
                )

                n_prior_well_cols = plate.nonempty_column_indices.index(
                                            plate_coords[1])
                offset_x = (
                    # Images in the current well left of the image
                    well_coords[1] * image_dimensions[1] +
                    # Potential overlap of images in y-direction
                    well_coords[1] * displacement +
                    # Wells in the current plate left of the current well
                    n_prior_well_cols * well_dimensions[1] +
                    # Gap introduced between wells
                    n_prior_well_cols * spacer_size +
                    # Potential shift of images to the right
                    shift_offset_x
                )

                job_ix = np.where(job_ids == j)[0]
                for ix in job_ix:
                    # Remove border objects
                    if border[ix]:
                        continue
                    # Reduce the number of outlines points
                    contour = np.array([coords_y[ix], coords_x[ix]]).T
                    poly = approximate_polygon(contour, 0.95).astype(int)
                    # Add offset to coordinates
                    global_coords[ix] = pd.DataFrame({
                        'y': poly[:, 0] + offset_y,
                        'x': poly[:, 1] + offset_x
                    }).sort_index(axis=1, ascending=False)
                    # NOTE: Columns of data frame have to be sorted, such that
                    # the y coordinate is in the first column and the x
                    # coordinate in the second. This makes it easy to convert
                    # it back into a numpy array as expected by many
                    # scikit-image functions, for example.

        return ObjectLayer(name, global_coords)

    def save(self, filename):
        '''
        Write the coordinates to the HDF5 layers file.

        The *y*, *x* coordinates of each object will be stored in a
        separate dataset of shape (n, 2), where n is the number of points
        on the perimeter sorted in counter-clockwise order.
        The name of the dataset is the global ID of the object, which
        corresponds to the column index of the object in the `features`
        dataset.
        The first column of the dataset contains the *y* coordinate and the
        second column the *x* coordinate. The dataset has an attribute called
        "columns" that holds the names of the two columns.

        Within the file the datasets are located in the subgroup "coordinates".
        So in case of objects called ``"cells"``
        ``/objects/cells/coordinates``.

        Parameters
        ----------
        filename: str
            absolute path to the HDF5 file

        See also
        --------
        :py:attribute:`tmlib.experiment.Experiment.layers_file`
        '''
        logger.info('save layer "%s" to HDF5 file', self.name)

        with DatasetWriter(filename) as data:
            for object_id, value in self.coordinates.iteritems():
                data.set_attribute(
                    'objects/{name}'.format(name=self.name),
                    name='visual_type', data='polygon'
                )
                path = '/objects/{name}/map_data/coordinates/{id}'.format(
                            name=self.name, id=object_id)
                data.write(path, value)
                data.set_attribute(
                    path, name='columns', data=value.columns.tolist()
                )
