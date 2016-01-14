import os
import numpy as np
import pandas as pd
import logging
import lxml
import itertools
from abc import ABCMeta
from cached_property import cached_property
from collections import defaultdict
from collections import OrderedDict
from skimage.measure import block_reduce
from skimage.measure import approximate_polygon
from .readers import DatasetReader
from .writers import DatasetWriter
from .errors import PyramidCreationError
from .errors import DataError
from .writers import ImageWriter
from .writers import XmlWriter
from .readers import NumpyImageReader
from .image_utils import convert_to_uint8

logger = logging.getLogger(__name__)


class Layer(object):

    '''
    Abstract base class for TissueMAPS layers.
    '''

    __metaclass__ = ABCMeta

    def __init__(self, experiment, image_displacement=0, well_spacer_size=500):
        '''
        Initialize an instance of class Layer.

        Parameters
        ----------
        experiment: tmlib.experiment.Experiment
            configured experiment object
        image_displacement: int, optional
            displacement in x, y direction in pixels between individual images;
            useful to account for an overlap between images (default: ``0``)
        well_spacer_size: int, optional
            number of pixels that should be introduced between wells
            (default: ``500``)
        '''
        self.experiment = experiment
        self.image_displacement = image_displacement
        self.well_spacer_size = well_spacer_size

    @cached_property
    def _non_empty_wells(self):
        # Empty wells will be filled with black tiles. However, if an entire
        # row or column is empty, the corresponding wells will be skipped.
        nonempty_rows = defaultdict(list)
        nonempty_cols = defaultdict(list)
        for p, plate in enumerate(self.experiment.plates):
            plate_grid = plate.grid
            # NOTE: all plate of an experiment must have the same layout, i.e.
            # the same number of wells and in case entire columns are
            # empty these must be same across all wells (e.g. for each plate
            # the outer rim of wells can be left out during image acquisition)
            nonempty_wells = np.where(plate_grid)
            r = tuple(np.unique(nonempty_wells[0]))
            nonempty_rows[r].append(plate.name)
            c = tuple(np.unique(nonempty_wells[1]))
            nonempty_cols[c].append(plate.name)

        if len(set([plate.n_wells for plate in self.experiment.plates])) > 1:
            raise PyramidCreationError('Layout of plates must be identical.')

        if len(nonempty_rows.keys()) > 1 or len(nonempty_cols.keys()) > 1:
            raise PyramidCreationError('Layout of plates must be identical.')

        return (list(nonempty_rows.keys()[0]), list(nonempty_cols.keys()[0]))

    @cached_property
    def image_dimensions(self):
        '''
        Returns
        -------
        Tuple[int]
            height, width of images in pixels
        '''
        cycle = self.experiment.plates[0].cycles[self.tpoint_ix]
        image = cycle.get_image_subset([0])[0]
        return image.pixels.dimensions

    @cached_property
    def well_dimensions(self):
        '''
        Returns
        -------
        Tuple[int]
            height, width of wells in pixels
        '''
        # Determine the dimensions of wells based on one example well.
        # NOTE: it is assumed that all wells have the same dimensions!
        cycle = self.experiment.plates[0].cycles[self.tpoint_ix]
        md = cycle.image_metadata
        n_rows = np.max(md.well_position_y) + 1
        n_cols = np.max(md.well_position_x) + 1
        return (
            n_rows * self.image_dimensions[0] +
            self.image_displacement * (n_rows - 1),
            n_cols * self.image_dimensions[1] +
            self.image_displacement * (n_cols - 1)
        )

    @cached_property
    def plate_dimensions(self):
        '''
        Returns
        -------
        Tuple[int]
            height, width of plates in pixels
        '''
        # Plate dimensions are defined as number of pixels along each
        # axis of the plate. Note that empty rows and columns are also
        # filled with "spacers", which has to be considered as well.
        plate = self.experiment.plates[0]
        n_nonempty_rows = len(plate.nonempty_row_indices)
        n_nonempty_cols = len(plate.nonempty_column_indices)
        plate_height = (
            n_nonempty_rows * self.well_dimensions[0] +
            # Spacer between wells
            (n_nonempty_rows - 1) * self.well_spacer_size
        )
        plate_width = (
            n_nonempty_cols * self.well_dimensions[1] +
            # Spacer between wells
            (n_nonempty_cols - 1) * self.well_spacer_size
        )
        return (plate_height, plate_width)

    def _calc_global_offset(self, plate_index, well_coords, n_prior_wells):
        # NOTE: the shifts between cycles must be added separately
        y_offset = (
            # Images in the well above the image
            well_coords[0] * self.image_dimensions[0] -
            # Potential overlap of images in y-direction
            well_coords[0] * self.image_displacement +
            # Wells in the plate above the well
            n_prior_wells[0] * self.well_dimensions[0] +
            # Gap introduced between wells
            n_prior_wells[0] * self.well_spacer_size +
            # Plates above the plate
            plate_index * self.plate_dimensions[0]
        )
        x_offset = (
            # Images in the well left of the image
            well_coords[1] * self.image_dimensions[1] -
            # Potential overlap of images in y-direction
            well_coords[1] * self.image_displacement +
            # Wells in the plate left of the well
            n_prior_wells[1] * self.well_dimensions[1] +
            # Gap introduced between wells
            n_prior_wells[1] * self.well_spacer_size
        )
        return (y_offset, x_offset)


class ChannelLayer(Layer):

    '''
    Class for creation of an image pyramid in zoomify format.

    A pyramid represents a large mosaic image by many small tiles at different
    resolution levels. Tiles are stored as JPEG files across several tile group
    directories.
    '''

    def __init__(self, experiment, tpoint_ix, channel_ix, zplane_ix,
                 zoom_factor=2, image_displacement=0, well_spacer_size=500):
        '''
        Initialize an instance of class ChannelLayer.

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
        zoom_factor: int, optional
            zoom factor between levels (default: ``2`)
        image_displacement: int, optional
            displacement in x, y direction in pixels between individual images;
            useful to account for an overlap between images (default: ``0``)
        well_spacer_size: int, optional
            number of pixels that should be introduced between wells
            (default: ``500``)
        '''
        super(ChannelLayer, self).__init__(
                experiment, image_displacement, well_spacer_size)
        self.experiment = experiment
        self.tpoint_ix = tpoint_ix
        self.channel_ix = channel_ix
        self.zplane_ix = zplane_ix
        self.zoom_factor = zoom_factor
        self.image_displacement = image_displacement
        self.well_spacer_size = well_spacer_size
        self.tile_size = 256

    @property
    def name(self):
        '''
        Returns
        -------
        str
            name of the pyramid
        '''
        return self.experiment.layer_names[
            (self.tpoint_ix, self.channel_ix, self.zplane_ix)
        ]

    @property
    def metadata(self):
        '''
        Returns
        -------
        tmlib.metadata.MosaicMetadata
            metadata of the pyramid
        '''
        return self.experiment.layer_metadata[self.name]

    @property
    def dir(self):
        '''
        Returns
        -------
        str
            absolute path to the pyramid directory
        '''
        directory = os.path.join(self.experiment.layers_dir, self.name)
        if not os.path.exists(directory):
            logger.debug('create layer directory: %s', directory)
            os.mkdir(directory)
        return directory

    def _calc_row_index_and_offset(self, y):
        start_fraction = (
            np.float(y) / np.float(self.tile_size)
        )
        start_index = int(np.floor(start_fraction))
        start_diff = start_index - start_fraction
        start_offset = int(self.tile_size * start_diff)

        end_fraction = (
            np.float(y + self.image_dimensions[0] - self.image_displacement) /
            np.float(self.tile_size)
        )
        end_index = int(np.ceil(end_fraction))
        end_diff = end_index - end_fraction
        end_offset = int(self.tile_size * end_diff)

        return {
            'start_index': start_index,
            'end_index': end_index,
            'start_offset': start_offset,
            'end_offset': end_offset
        }

    def _calc_col_index_and_offset(self, x):
        start_fraction = (
            np.float(x) / np.float(self.tile_size)
        )
        start_index = int(np.floor(start_fraction))
        start_diff = start_index - start_fraction
        start_offset = int(self.tile_size * start_diff)

        end_fraction = (
            np.float(x + self.image_dimensions[1] - self.image_displacement) /
            np.float(self.tile_size)
        )
        end_index = int(np.ceil(end_fraction))
        end_diff = end_index - end_fraction
        end_offset = int(self.tile_size * end_diff)

        return {
            'start_index': start_index,
            'end_index': end_index,
            'start_offset': start_offset,
            'end_offset': end_offset
        }

    @property
    def base_tile_image_mappings(self):
        '''
        Returns
        -------
        Dict[str, Dict[Tuple[int] or str, List[Dict[str or int] or Tuple[int]]]
            mapping to retrieve information about images (name and y,x offsets)
            for a given tile defined by its row, column coordinate and
            mapping to retrieve tile coordinates for a given image name
        '''
        cycle = self.experiment.plates[0].cycles[self.tpoint_ix]
        md = cycle.image_metadata

        tile_mapper = defaultdict(list)
        image_mapper = defaultdict(list)
        for p, plate in enumerate(self.experiment.plates):

            logger.info('map pyramid tiles to images of '
                        'channel #%d and z-plane #%d belonging to plate "%s"',
                        self.channel_ix, self.zplane_ix, plate.name)

            h = range(plate.grid.shape[0])
            w = range(plate.grid.shape[1])
            for i, j in itertools.product(h, w):

                if i not in self._non_empty_wells[0]:
                    logger.debug('skip empty plate row # %d', i)
                    continue

                if j not in self._non_empty_wells[1]:
                    logger.debug('skip empty plate column # %d', j)
                    continue

                well = plate.grid[i, j]
                if well is None:
                    logger.debug('skip empty well "%s"',
                                 plate.map_well_coordinate_to_id((i, j)))
                    continue

                logger.debug('well "%s"', well)
                n_prior_wells_y = plate.nonempty_row_indices.index(i)
                n_prior_wells_x = plate.nonempty_column_indices.index(j)
                prior_wells = (n_prior_wells_y, n_prior_wells_x)

                index = np.where(
                            (md['tpoint_ix'] == self.tpoint_ix) &
                            (md['channel_ix'] == self.channel_ix) &
                            (md['zplane_ix'] == self.zplane_ix) &
                            (md['well_name'] == well)
                )[0]

                for ix in index:
                    image_name = md.ix[ix, 'name']
                    logger.debug('map tiles for image "%s"', image_name)
                    well_coords = (
                        md.ix[ix, 'well_position_y'],
                        md.ix[ix, 'well_position_x']
                    )
                    y, x = self._calc_global_offset(
                                p, well_coords, prior_wells)
                    logger.debug('image offset: (%d, %d)', y, x)

                    # Map the image to the corresponding tiles.
                    row_info = self._calc_row_index_and_offset(y)
                    col_info = self._calc_col_index_and_offset(x)
                    rows = range(row_info['start_index'],
                                 row_info['end_index'])
                    cols = range(col_info['start_index'],
                                 col_info['end_index'])
                    for r, row in enumerate(rows):
                        for c, col in enumerate(cols):
                            if row == row_info['end_index']:
                                y_offset = row_info['end_offset']
                            else:
                                y_offset = row_info['start_offset'] + \
                                                r * self.tile_size

                            if col == col_info['end_index']:
                                x_offset = col_info['end_offset']
                            else:
                                x_offset = col_info['start_offset'] + \
                                                c * self.tile_size

                            tile_mapper[(row, col)].append({
                                'name': image_name,
                                'y_offset': y_offset,
                                'x_offset': x_offset
                            })

                            image_mapper[image_name].append(
                                (row, col)
                            )

        return {
            'tile_to_images': tile_mapper,
            'image_to_tiles': image_mapper
        }

    def _extract_tile_from_image(self, image, y_offset, x_offset):
        # Some tiles may lie on the border of wells and contain spacer
        # background pixels. The pixel offset for the corresponding
        # images will be negative. The missing pixels will be padded
        # with zeros.
        y_end = y_offset + self.tile_size
        x_end = x_offset + self.tile_size
        y_pad_top = None
        y_pad_bottom = None
        x_pad_left = None
        x_pad_right = None
        if y_offset < 0:
            height = abs(y_offset)
            if x_offset < 0:
                width = self.tile_size - abs(x_offset)
            elif x_end > image.pixels.dimensions[1]:
                width = self.tile_size - (x_end - image.pixels.dimensions[1])
            else:
                width = self.tile_size
            y_pad_top = np.zeros((height, width), dtype=image.pixels.dtype)
            y_offset = 0
        elif (image.pixels.dimensions[0] - y_offset) < self.tile_size:
            height = self.tile_size - (image.pixels.dimensions[0] - y_offset)
            if x_offset < 0:
                width = self.tile_size - abs(x_offset)
            elif x_end > image.pixels.dimensions[1]:
                width = self.tile_size - (x_end - image.pixels.dimensions[1])
            else:
                width = self.tile_size
            y_pad_bottom = np.zeros((height, width), dtype=image.pixels.dtype)
        if x_offset < 0:
            height = self.tile_size
            width = abs(x_offset)
            x_pad_left = np.zeros((height, width), dtype=image.pixels.dtype)
            x_offset = 0
        elif (image.pixels.dimensions[1] - x_offset) < self.tile_size:
            height = self.tile_size
            width = self.tile_size - (image.pixels.dimensions[1] - x_offset)
            x_pad_right = np.zeros((height, width), dtype=image.pixels.dtype)

        tile = image.pixels.array[y_offset:y_end, x_offset:x_end]

        if y_pad_top is not None:
            tile = np.vstack([y_pad_top, tile])
        if y_pad_bottom is not None:
            tile = np.vstack([tile, y_pad_bottom])
        if x_pad_left is not None:
            tile = np.hstack([x_pad_left, tile])
        if x_pad_right is not None:
            tile = np.hstack([tile, x_pad_right])

        return tile

    def create_base_tiles(self, clip_value=None, illumcorr=False, align=False,
                          image_indices=None):
        '''
        Create the tiles for the highest resolution level, i.e. the base of
        the image pyramid, using the original microscope images.

        Parameters
        ----------
        clip_value: int, optional
            fixed threshold value (default: ``None``)
        illumcorr: bool, optional
            whether images should be corrected for illumination artifacts
            (default: ``False``)
        align: bool, optional
            whether images should be aligned between cycles
            (default: ``False``)
        image_indices: List[int], optional
            zero-based indices of images that should be processed;
            if not provided, all images will be processed by default
            (default: ``None``)

        Note
        ----
        Tiles are created without actually stitching images together.
        Thereby, maximally 4 images need to be loaded into memory at a time.
        This keeps memory requirements to a minimum and allows parallelization
        of the pyramid creation step.
        '''
        # TODO: parallelize over image files
        logger.info('create tiles for level %d', len(self.zoom_level_info) - 1)

        if clip_value is None:
            logger.debug('set default clip value')
            clip_value = 2**16
        logger.info('clip intensity values above %d', clip_value)

        # 1) Process missing tiles, i.e. tiles not mapping to any images.
        # They represent empty sites corresponding to well spacers and will
        # simply be filled with black pixels.
        logger.debug('create empty tiles')
        tile_coords = self.base_tile_image_mappings['tile_to_images'].keys()
        n_rows = self.zoom_level_info[-1]['n_tiles_height']
        n_cols = self.zoom_level_info[-1]['n_tiles_width']
        all_tile_coords = list(itertools.product(range(n_rows), range(n_cols)))
        missing_tile_coords = set(all_tile_coords) - set(tile_coords)
        for t in missing_tile_coords:
            tile = np.zeros((self.tile_size, self.tile_size), dtype=np.uint8)
            tile_file = self.tile_files[-1][t]
            with ImageWriter(self.dir) as writer:
                writer.write(tile_file, tile)

        # 2) Process tiles that that map to one or more images.
        logger.debug('create non-empty tiles')
        cycle = self.experiment.plates[0].cycles[self.tpoint_ix]
        md = cycle.image_metadata
        if image_indices is None:
            filenames = self.metadata.filenames
        else:
            filenames = np.array(self.metadata.filenames)[image_indices]
        for f in filenames:
            name = os.path.basename(f)
            logger.debug('create tiles mapping to image "%s"', name)
            # Retrieve the coordinates of the corresponding tiles
            tile_coords = self.base_tile_image_mappings['image_to_tiles'][name]
            # Create individual tiles
            for t in tile_coords:
                logger.debug('create tile for column %d, row %d', t[1], t[0])
                # Determine location of the tile within the image
                image_info = self.base_tile_image_mappings['tile_to_images'][t]
                # A tile may be composed of pixels of multiple images
                # TODO: prevent loading the images several times
                names = [im['name'] for im in image_info]
                indices = [np.where(md['name'] == n)[0][0] for n in names]
                images = cycle.get_image_subset(indices)
                tiles = list()
                for i, img in enumerate(images):
                    if illumcorr:
                        # Correct image for illumination artifacts
                        img = img.correct()
                    if align:
                        # Align image between cycles
                        img = img.align(crop=False)
                    y_offset = image_info[i]['y_offset']
                    x_offset = image_info[i]['x_offset']
                    # We use the same approach for overlapping and
                    # non-overlapping tiles, i.e. tiles that are composed
                    # of pixels of a single image and those that contain pixels
                    # of multiple images, and then deal with the overlap later.
                    tiles.append(
                        self._extract_tile_from_image(
                                img, y_offset, x_offset)
                    )
                tiles = np.array(tiles)

                if len(tiles) > 1:
                    # If a tile is composed of pixels of multiple images
                    # we need to extract the relevant pixels and join them
                    logger.debug('tile overlaps multiple images')
                    y_offsets = np.array([im['y_offset'] for im in image_info])
                    x_offsets = np.array([im['x_offset'] for im in image_info])
                    vert = y_offsets < 0
                    horz = x_offsets < 0
                    # Take the top left tile and then insert the other pixels
                    y_pos = [md.ix[i, 'well_position_y'] for i in indices]
                    x_pos = [md.ix[i, 'well_position_x'] for i in indices]
                    ix_top = np.where(np.array(y_pos) == np.min(y_pos))[0]
                    ix_left = np.where(np.array(x_pos) == np.min(x_pos))[0]
                    ix_top_left = list(set(ix_top).intersection(ix_left))[0]
                    tile = tiles[ix_top_left]
                    if len(ix_top) == 1:
                        logger.debug('2 images: vertical overlap')
                        y = abs(y_offsets[vert][0]) - self.tile_size
                        tile[y:, :] = tiles[vert][0][y:, :]
                    elif len(ix_left) == 1:
                        logger.debug('2 images: horizontal overlap')
                        x = abs(x_offsets[horz][0])
                        tile[:, x:] = tiles[horz][0][:, x:]
                    else:
                        logger.debug('4 images: vertical & horizontal overlap')
                        y = abs(y_offsets[vert][0]) - self.tile_size
                        x = abs(x_offsets[horz][0])
                        tile[y:, x:] = tiles[vert & horz][0][y:, x:]
                        tile[y:, :x] = tiles[vert & ~horz][0][y:, :x]
                        tile[:y, x:] = tiles[~vert & horz][0][:y, x:]
                        tile[:y, :x] = tiles[~vert & ~horz][0][:y, :x]
                else:
                    tile = tiles[0]

                # Clip intensity values
                logger.debug('clip intensity values')
                tile = np.clip(tile, 0, clip_value)
                # Rescale intensity values to 8-bit
                logger.debug('rescale intensity values to 8-bit')
                tile = convert_to_uint8(tile, 0, clip_value)
                # Write tile to file on disk
                tile_file = self.tile_files[-1][t]
                with ImageWriter(self.dir) as writer:
                    writer.write(tile_file, tile)

    def create_downsampled_tiles(self, level):
        '''
        The tiles for lower resolution levels are created using the tiles from
        the next higher level. To this end, n x n tiles are loaded and stitched
        to form a mosaic, which is subsequently down-sampled to form the next
        lower level tile. For a zoom factor of 2, a mosaic based on 2x2 tiles
        is created and reduced to a single tile.

        Parameters
        ----------
        level: int
            zero-based zoom level index
        '''
        logger.info('create tiles for level %d', level)
        block_size = (self.zoom_factor, self.zoom_factor)
        for t, tile_file in self.tile_files[level].iteritems():
            logger.debug('create tile for column %d, row %d', t[1], t[0])
            row = t[0]
            col = t[1]
            rows = range(
                    row * self.zoom_factor,
                    (row * self.zoom_factor + self.zoom_factor - 1) + 1
            )
            cols = range(
                    col * self.zoom_factor,
                    (col * self.zoom_factor + self.zoom_factor - 1) + 1
            )
            # Build the mosaic by loading the required higher level tiles and
            # stitching them together
            with NumpyImageReader(self.dir) as reader:
                mosaic = None
                for i, r in enumerate(rows):
                    row_image = None
                    for j, c in enumerate(cols):
                        # Some calculated coordinates may not exist
                        try:
                            filename = self.tile_files[level+1][(r, c)]
                        except:
                            continue
                        image = reader.read(filename)
                        if row_image is None:
                            row_image = image
                        else:
                            row_image = np.hstack([row_image, image])
                    if row_image is None:
                        continue
                    if mosaic is None:
                        mosaic = row_image
                    else:
                        mosaic = np.vstack([mosaic, row_image])
            # Create the tile at the current level by downsampling the mosaic
            tile = block_reduce(mosaic, block_size, func=np.mean)
            # Write the tile to file on disk
            with ImageWriter(self.dir) as writer:
                writer.write(tile_file, tile)

    def create_tile_groups(self):
        '''
        Create all required tile group directories.

        Raises
        ------
        OSError
            when a tile group directory already exists
        '''
        for i in range(self.n_tile_groups):
            name = self.build_tile_group_name(i)
            tile_dir = os.path.join(self.dir, name)
            if os.path.exists(tile_dir):
                raise OSError('Tile directory already exists: %s' % self.dir)
            os.mkdir(tile_dir)

    def create_image_properties_file(self):
        '''
        Create the image properties XML file, which provides meta-information
        about the pyramid, such as the dimensions of the highest resolution
        level and the total number of tiles.
        '''
        root = lxml.etree.Element(
                    'IMAGE_PROPERTIES',
                    WIDTH=str(self.zoom_level_info[-1]['n_pixels_width']),
                    HEIGHT=str(self.zoom_level_info[-1]['n_pixels_height']),
                    NUMTILES=str(self.n_tiles),
                    NUMIMAGES=str(1),
                    VERSION='1.8',
                    TILESIZE=str(self.tile_size)
        )
        xml_string = lxml.etree.tostring(root)
        with XmlWriter(self.dir) as writer:
            writer.write('ImageProperties.xml', xml_string)

    @staticmethod
    def build_tile_group_name(index):
        '''
        Build the directory name for the *i*-th tile group.

        Parameters
        ----------
        index: int
            zero-based tile group index

        Returns
        -------
        str
            tile group folder name
        '''
        return 'TileGroup{i}'.format(i=index)

    @staticmethod
    def build_tile_name(level, row, col):
        '''
        Build the file name for an image tile.

        Parameters
        ----------
        level: int
            zero-based zoom level
        row: int
            zero-based row index of the tile at the given zoom `level`
        col: int
            zero-based column index of the tile at the given zoom `level`

        Returns
        -------
        str
            image tile file name
        '''
        return '{level}-{col}-{row}.jpg'.format(level=level, col=col, row=row)

    @property
    def n_tiles(self):
        '''
        Returns
        -------
        int
            total number of tiles across all resolution levels
        '''
        return np.sum(
            [level['n_tiles'] for level in self.zoom_level_info]
        )

    @property
    def n_tile_groups(self):
        '''
        Returns
        -------
        int
            total number of tile groups
        '''
        return int(np.ceil(np.float(self.n_tiles) / 256))

    @property
    def mosaic_dimensions(self):
        '''
        Returns
        -------
        Tuple[int]
            number of pixels along the horizontal and vertical dimensions of
            the stitched mosaic at the highest resolution level
        '''
        height = self.plate_dimensions[0] * len(self.experiment.plates)
        width = self.plate_dimensions[1]
        return (height, width)

    def _collect_zoom_level_info(self, height, width):
        rows = int(np.ceil(np.float(height) / np.float(self.tile_size)))
        cols = int(np.ceil(np.float(width) / np.float(self.tile_size)))
        return {
            'n_pixels_height': height,
            'n_pixels_width': width,
            'n_pixels': height * width,
            'n_tiles_height': rows,
            'n_tiles_width': cols,
            'n_tiles': rows * cols
        }

    @property
    def zoom_level_info(self):
        '''
        Returns
        -------
        List[Dict[str, int]]
            information about each zoom level, such as the number of pixels
            and tiles along the vertical and horizontal axis of the pyramid,
            sorted such that the first element represents the lowest resolution
            (maximally zoomed out) level and the last element the highest
            resolution (maximally zoomed in) level
        '''
        height = self.mosaic_dimensions[0]
        width = self.mosaic_dimensions[1]
        levels = list()
        info = self._collect_zoom_level_info(height, width)
        levels.append(info)
        while height > self.tile_size or width > self.tile_size:
            # Calculate the number of pixels along each axis
            height = int(np.ceil(np.float(height) / self.zoom_factor))
            width = int(np.ceil(np.float(width) / self.zoom_factor))
            # Calculate the number of tiles along each axis (row and column)
            info = self._collect_zoom_level_info(height, width)
            levels.append(info)
        return list(reversed(levels))

    @property
    def tile_files(self):
        '''
        Returns
        -------
        List[Dict[Tuple[int], str]]
            path to the tile files relative to `pyramid_dir` for each
            row, column coordinate at each zoom level, sorted such that the
            first element represents the lowest resolution
            (maximally zoomed out) level
        '''
        n = 0
        tiles = list()
        for i, level in enumerate(self.zoom_level_info):
            # Build the grid for the layout of the tiles
            n_rows = level['n_tiles_height']
            n_cols = level['n_tiles_width']
            grid = dict()
            tiles.append(grid)
            for r, c in itertools.product(range(n_rows), range(n_cols)):
                # Each tile group directory holds maximally 256 files and
                # groups are filled up from top to bottom, starting at 0 for
                # the most zoomed out tile and then increasing monotonically
                # in a row wise
                index = n // 256
                group = self.build_tile_group_name(index)
                filename = self.build_tile_name(i, r, c)
                tiles[i][(r, c)] = os.path.join(group, filename)
                n += 1
        return tiles


class ObjectLayer(object):

    '''
    Class for creation of object outline coordinates, which are based on
    image segmentation. Coordinates are stored in a HDF5 file.
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

        Write coordinates of object contours to the HDF5 data file:
        The *y*, *x* coordinates of each object will be stored in a
        separate dataset of shape (n, 2), where n is the number of points
        on the perimeter sorted in counter-clockwise order.
        The name of the dataset is the global ID of the object, which
        corresponds to the row index of the object in the `features`
        dataset.
        The first column of the dataset contains the *y* coordinate and the
        second column the *x* coordinate. The dataset has an attribute called
        "columns" that holds the names of the two columns.

        Within the file the datasets are located in the subgroup "coordinates":
        ``/objects/<object_name>/map_data/coordinates/<object_id>``.

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
        segm_path = '/objects/%s/segmentation' % name
        with DatasetWriter(filename) as out:
            out.set_attribute(
                '/objects/%s' % name,
                name='visual_type', data='polygon'
            )
            coordinates_path = '/objects/%s/map_data/coordinates' % name
            with DatasetReader(filename) as data:
                if not data.exists(segm_path):
                    raise DataError(
                        'The data file does\'t contain any segmentations: %s'
                        % segm_path)
                # Get the dimensions of the original, unaligned image
                image_dimensions = (
                    data.read('/metadata/image_dimension_y', index=0),
                    data.read('/metadata/image_dimension_x', index=0)
                )
                # Get the indices of objects at the border of images
                # (using the parent objects as references)
                if 'parent_name' in data.list_datasets(segm_path):
                    parent = data.read('%s/parent_name' % segm_path, index=0)
                    p_segmentation_path = '/objects/%s/segmentation' % parent
                    is_border = data.read('%s/is_border' % p_segmentation_path)
                else:
                    is_border = data.read('%s/is_border' % segm_path)

                # Get the coordinates of object outlines relative to individual
                # images
                coords_y = data.read('%s/outlines/y' % segm_path)
                coords_x = data.read('%s/outlines/x' % segm_path)

                # A jterator job represents a unique image acquisition site.
                # We have to identify the position of each site within the
                # overall acquisition grid and update the outline coordinates
                # accordingly, i.e. translate site-specific coordinates into
                # global ones.

                # Get the dimensions of wells from one example well.
                # NOTE: It's assumed that all wells have the same dimensions!
                cycle = experiment.plates[0].cycles[0]
                md = cycle.image_metadata
                well_name = data.read('/metadata/well_name', index=0)
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
                    n_rows * image_dimensions[0] - displacement * (n_rows - 1),
                    n_cols * image_dimensions[1] - displacement * (n_cols - 1)
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
                job_ids = data.read('%s/job_ids' % segm_path)
                global_coords = OrderedDict()
                for j in np.unique(job_ids):
                    logger.debug('process image acquisition site # %d', j)
                    index = j - 1  # job indices are one-based

                    plate_name = data.read('metadata/plate_name', index=index)
                    plate_index = plate_names.index(plate_name)
                    well_name = data.read('metadata/well_name', index=index)
                    plate_coords = plate.map_well_id_to_coordinate(well_name)
                    well_coords = (
                        data.read('metadata/well_position_y', index=index),
                        data.read('metadata/well_position_x', index=index)
                    )
                    logger.debug('plate name: %s', plate_name)
                    logger.debug('plate coorinates: {0}'.format(plate_coords))
                    logger.debug('well name: %s', plate_name)
                    logger.debug('well coorinates: {0}'.format(well_coords))

                    # Images may have been aligned and the resulting shift must
                    # be accounted for.
                    shift_offset_y = data.read('/metadata/shift_offset_y',
                                               index=index)
                    shift_offset_x = data.read('metadata/shift_offset_x',
                                               index=index)

                    n_prior_well_rows = plate.nonempty_row_indices.index(
                                                plate_coords[0])
                    offset_y = (
                        # Images in the well above the image
                        well_coords[0] * image_dimensions[0] -
                        # Potential overlap of images in y-direction
                        well_coords[0] * displacement +
                        # Wells in the plate above the well
                        n_prior_well_rows * well_dimensions[0] +
                        # Gap introduced between wells
                        n_prior_well_rows * spacer_size +
                        # Potential shift of images downwards
                        shift_offset_y +
                        # Plates above the plate
                        plate_index * plate_dimensions[0]
                    )
                    logger.debug('y offset: %d', offset_y)

                    n_prior_well_cols = plate.nonempty_column_indices.index(
                                                plate_coords[1])

                    offset_x = (
                        # Images in the well left of the image
                        well_coords[1] * image_dimensions[1] -
                        # Potential overlap of images in y-direction
                        well_coords[1] * displacement +
                        # Wells in the plate left of the well
                        n_prior_well_cols * well_dimensions[1] +
                        # Gap introduced between wells
                        n_prior_well_cols * spacer_size +
                        # Potential shift of images to the right
                        shift_offset_x
                    )
                    logger.debug('x offset: %d', offset_x)

                    job_ix = np.where(job_ids == j)[0]
                    for ix in job_ix:
                        # Border objects should not be displayed
                        if is_border[ix]:
                            continue
                        # Reduce the number of outlines points
                        contour = np.array([coords_y[ix], coords_x[ix]]).T
                        poly = approximate_polygon(contour, 0.95).astype(int)
                        # Add offset to coordinates
                        global_coordinates = pd.DataFrame({
                            'y': -1 * (poly[:, 0] + offset_y),
                            'x': poly[:, 1] + offset_x
                        })
                        # Openlayers wants the x coordinate in the first column
                        # and the inverted y coordinate in the second.
                        path = '%s/%d' % (coordinates_path, ix)
                        out.write(path, data=global_coordinates)
                        out.set_attribute(
                            path, name='columns',
                            data=global_coordinates.columns.tolist()
                        )

                # Store the objects separately as a sorted array of integers
                global_obj_ids = map(int, data.list_datasets(coordinates_path))
                obj_ids_path = '/objects/%s/ids' % name
                out.write(obj_ids_path, data=sorted(global_obj_ids))

        return ObjectLayer(name, global_coords)
