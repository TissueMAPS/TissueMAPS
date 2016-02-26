import os
import re
import numpy as np
import pandas as pd
import logging
import lxml
import itertools
import skimage.measure
from abc import ABCMeta
from abc import abstractmethod
from cached_property import cached_property
from collections import defaultdict
from .readers import DatasetReader
from .errors import PyramidCreationError
from .errors import RegexError
from .writers import ImageWriter
from .writers import DatasetWriter
from .writers import XmlWriter
from .readers import NumpyImageReader

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
        cycle = self.experiment.plates[0].cycles[0]
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
        cycle = self.experiment.plates[0].cycles[0]
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

        Warning
        -------
        The values for `well_spacer_size` and `image_displacement`
        must be the same as for the other layers,
        otherwise objects and images will not align.
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

    @cached_property
    def base_tile_mappings(self):
        '''
        Returns
        -------
        Dict[str, Dict[Tuple[int] or str, List[Dict[str or int] or Tuple[int]]]
            "tile_to_images" mapping to retrieve information about images
            (name and y,x offsets) for a given tile defined by its row, column
            coordinate and "image_to_tiles" mapping to retrieve tile coordinates
            for a given image name
        '''
        cycle = self.experiment.plates[0].cycles[self.tpoint_ix]
        md = cycle.image_metadata

        tile_mapper = defaultdict(list)
        image_mapper = defaultdict(list)
        for p, plate in enumerate(self.experiment.plates):

            logger.debug('map base tiles to images of plate "%s"',
                         plate.name)

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

                logger.debug('map base tiles to images of well "%s"', well)
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
                    logger.debug('map base tiles for image "%s"', image_name)
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

    def get_level_and_coordinate(self, tile_filename):
        '''
        Determine "level", "row", and "column" indices from tile filename
        using a regular expression.

        Parameters
        ----------
        tile_filename: str
            name of a pyramid tile

        Returns
        -------
        Dict[str, int]
            zero-based indices for "level", "row", and "column" of a given tile

        Raises
        ------
        tmlib.errors.RegexError
            when indices cannot be determined from filename
        '''
        r = re.compile('(?P<level>\d+)-(?P<column>\d+)-(?P<row>\d+).jpg')
        m = r.search(tile_filename).groupdict()
        if not m:
            RegexError(
                'Indices could not be determined from file: %s'
                % tile_filename)
        return {k: int(v) for k, v in m.iteritems()}

    def _determine_higher_level_coordinates(self, level, row, column):
        coordinates = list()
        existing_coordinates = self.tile_files[level + 1].keys()
        rows = range(
                row * self.zoom_factor,
                (row * self.zoom_factor + self.zoom_factor - 1) + 1
        )
        cols = range(
                column * self.zoom_factor,
                (column * self.zoom_factor + self.zoom_factor - 1) + 1
        )
        for r, c in itertools.product(rows, cols):
            if (r, c) in existing_coordinates:
                coordinates.append((r, c))
        return coordinates

    def get_tiles_of_next_higher_level(self, filename):
        '''
        Get the tiles of the next higher level that make up the given tile.

        Parameters
        ----------
        filename: str
            name of the tile file

        Returns
        -------
        List[Tuple[int]
            row, column coordinates for the tiles of the next higher resolution
            level for a given a tile
        '''
        logger.debug('map tile %s to tiles of next higher level', filename)
        indices = self.get_level_and_coordinate(filename)
        level = indices['level']
        row = indices['row']
        col = indices['column']
        # Determine the row, column coordinate of the tiles of the next
        # higher resolution level
        return self._determine_higher_level_coordinates(level, row, col)

    def _extract_tile_from_image(self, image, y_offset, x_offset):
        # Some tiles may lie on the border of wells and contain spacer
        # background pixels. The pixel offset for the corresponding
        # images will be negative. The missing pixels will be padded
        # with zeros.
        y_end = y_offset + self.tile_size
        x_end = x_offset + self.tile_size

        n_top = None
        n_bottom = None
        n_left = None
        n_right = None
        if y_offset < 0:
            n_top = abs(y_offset)
            y_offset = 0
        elif (image.pixels.dimensions[0] - y_offset) < self.tile_size:
            n_bottom = self.tile_size - (image.pixels.dimensions[0] - y_offset)
        if x_offset < 0:
            n_left = abs(x_offset)
            x_offset = 0
        elif (image.pixels.dimensions[1] - x_offset) < self.tile_size:
            n_right = self.tile_size - (image.pixels.dimensions[1] - x_offset)

        tile = image.pixels.extract(
                    y_offset, x_offset, y_end-y_offset, x_end-x_offset)

        if n_top is not None:
            tile = tile.add_background(n_top, 'top')
        if n_bottom is not None:
            tile = tile.add_background(n_bottom, 'bottom')
        if n_left is not None:
            tile = tile.add_background(n_left, 'left')
        if n_right is not None:
            tile = tile.add_background(n_right, 'right')

        return tile

    @property
    def n_zoom_levels(self):
        '''
        Returns
        -------
        int
            number of zoom levels
        '''
        return len(self.zoom_level_info)

    @property
    def base_level_index(self):
        '''
        Returns
        -------
        int
            zero-based index of the base level, i.e. the most zoomed in level
            with the highest resolution
        '''
        return len(self.zoom_level_info) - 1

    def create_empty_base_tiles(self, clip_value=None):
        '''
        Create empty tiles for the highest resolution level that do not map
        that do not map to an image.

        Parameters
        ----------
        clip_value: int, optional
            fixed threshold value (default: ``None``)
        '''
        logger.debug('create empty tiles for level %d', self.base_level_index)
        tile_coords = self.base_tile_mappings['tile_to_images'].keys()
        n_rows = self.zoom_level_info[-1]['n_tiles_height']
        n_cols = self.zoom_level_info[-1]['n_tiles_width']
        all_tile_coords = list(itertools.product(range(n_rows), range(n_cols)))
        missing_tile_coords = set(all_tile_coords) - set(tile_coords)
        for t in missing_tile_coords:
            tile = np.zeros((self.tile_size, self.tile_size), dtype=np.uint8)
            tile_file = self.tile_files[-1][t]
            with ImageWriter(self.dir) as writer:
                writer.write(tile_file, tile)

    def create_base_tiles(self, clip_value=None, illumcorr=False, align=False,
                          subset_indices=None):
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
        subset_indices: List[int], optional
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
        logger.info('create tiles for level %d', self.base_level_index)
        if illumcorr:
            logger.info('correct images for illumination artifacts')
        if align:
            logger.info('align images between cycles')

        if clip_value is None:
            logger.debug('set default clip value')
            clip_value = 2**16
        logger.info('clip intensity values above %d', clip_value)

        # Process tiles that map to one or more images.
        cycle = self.experiment.plates[0].cycles[self.tpoint_ix]
        if illumcorr:
            stats = cycle.illumstats_images[self.channel_ix]
        md = cycle.image_metadata
        if subset_indices is None:
            logger.info('process all image files')
            filenames = self.metadata.filenames
        else:
            logger.info('process subset of image files')
            filenames = list(np.array(self.metadata.filenames)[subset_indices])
        for f in filenames:
            name = os.path.basename(f)
            logger.debug('create tiles mapping to image "%s"', name)
            # Retrieve the coordinates of the corresponding tiles
            tile_coords = self.base_tile_mappings['image_to_tiles'][name]
            # Determine location of the tile within the image
            image_info = self.base_tile_mappings['tile_to_images']
            # Create individual tiles
            indices = None
            for t in tile_coords:
                logger.debug('create tile for column %d, row %d', t[1], t[0])
                # A tile may be composed of pixels of multiple images:
                # load all required images
                names = [im['name'] for im in image_info[t]]
                # Cache images to prevent reloading when not necessary
                new_indices = [np.where(md['name'] == n)[0][0] for n in names]
                if indices is None or indices != new_indices:
                    indices = new_indices
                    images = cycle.get_image_subset(indices)
                    for i, img in enumerate(images):
                        if illumcorr:
                            # Correct image for illumination artifacts
                            # NOTE: This is the bottleneck. Can we make this
                            # faster? Cython: static types? Vips?
                            images[i] = img.correct(stats)
                        if align:
                            # Align image between cycles
                            images[i] = img.align(crop=False)
                tiles = list()
                for i, img in enumerate(images):
                    y_offset = image_info[t][i]['y_offset']
                    x_offset = image_info[t][i]['x_offset']
                    # We use the same approach for overlapping and
                    # non-overlapping tiles, i.e. tiles that are composed
                    # of pixels of a single image and those that contain pixels
                    # of multiple images, and then deal with the overlap later.
                    tiles.append(
                        self._extract_tile_from_image(
                                img, y_offset, x_offset)
                    )
                    # NOTE: a tile of type tmlib.pixels.Pixels
                tiles = np.array(tiles)

                if len(tiles) > 1:
                    # If a tile is composed of pixels of multiple images
                    # we need to extract the relevant pixels and join them
                    logger.debug('tile overlaps multiple images')
                    y_offsets = np.array([
                                    im['y_offset'] for im in image_info[t]
                    ])
                    x_offsets = np.array([
                                    im['x_offset'] for im in image_info[t]
                    ])
                    v = y_offsets < 0
                    h = x_offsets < 0
                    # Take the top left tile and then merge the relevant
                    # pixels of the other tiles into it
                    y_pos = [md.ix[i, 'well_position_y'] for i in indices]
                    x_pos = [md.ix[i, 'well_position_x'] for i in indices]
                    ix_top = np.where(np.array(y_pos) == np.min(y_pos))[0]
                    ix_left = np.where(np.array(x_pos) == np.min(x_pos))[0]
                    ix_top_left = list(set(ix_top).intersection(ix_left))[0]
                    tile = tiles[ix_top_left]
                    if len(ix_top) == 1:
                        logger.debug('2 images: vertical overlap')
                        offset = abs(y_offsets[v][0])
                        lower = tiles[v][0]
                        tile = tile.merge(lower, 'vertical', offset)
                    elif len(ix_left) == 1:
                        logger.debug('2 images: horizontal overlap')
                        offset = abs(x_offsets[h][0])
                        right = tiles[h][0]
                        tile = tile.merge(right, 'horizontal', offset)
                    else:
                        logger.debug('4 images: vertical & horizontal overlap')
                        h_offset = abs(x_offsets[h][0])
                        right_upper = tiles[~v & h][0]
                        upper = tile.merge(right_upper, 'horizontal', h_offset)
                        left_lower = tiles[v & ~h][0]
                        right_lower = tiles[v & h][0]
                        lower = left_lower.merge(right_lower, 'horizontal', h_offset)
                        v_offset = abs(y_offsets[v][0])
                        tile = upper.merge(lower, 'vertical', v_offset)
                else:
                    tile = tiles[0]

                # Clip intensity values and rescale to 8-bit
                logger.debug('clip intensity values')
                tile = tile.clip(clip_value)
                logger.debug('rescale intensity values to 8-bit')
                tile = tile.scale(clip_value)
                # Write tile to file on disk
                tile_file = os.path.join(self.dir, self.tile_files[-1][t])
                logger.debug('write tile to file: "%s"', tile_file)
                tile.write_to_file(tile_file)

    def create_downsampled_tiles(self, level, subset_indices=None):
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
        subset_indices: List[int], optional
            zero-based indices of tiles that should be processed;
            if not provided, all tiles will be processed by default
            (default: ``None``)
        '''
        logger.info('create tiles for level %d', level)
        block_size = (self.zoom_factor, self.zoom_factor)
        tile_info = self.tile_files[level]
        pre_tile_files = self.tile_files[level + 1]
        if subset_indices is None:
            filenames = tile_info.values()
        else:
            filenames = list(np.array(tile_info.values())[subset_indices])
        for f in filenames:
            logger.debug('create tile "%s"', f)
            coordinates = self.get_tiles_of_next_higher_level(f)
            rows = np.unique([c[0] for c in coordinates])
            cols = np.unique([c[1] for c in coordinates])
            # Build the mosaic by loading the required higher level tiles
            # (created in a previous run) and stitching them together
            with NumpyImageReader(self.dir) as reader:
                for i, r in enumerate(rows):
                    for j, c in enumerate(cols):
                        pre_tile_filename = pre_tile_files[(r, c)]
                        image = reader.read(pre_tile_filename)
                        if j == 0:
                            row_image = image
                        else:
                            row_image = np.hstack([row_image, image])
                    if i == 0:
                        mosaic = row_image
                    else:
                        mosaic = np.vstack([mosaic, row_image])
            # Create the tile at the current level by downsampling the mosaic
            tile = skimage.measure.block_reduce(mosaic, block_size, func=np.mean)
            # Write the tile to file on disk
            with ImageWriter(self.dir) as writer:
                writer.write(f, tile)

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
            if not os.path.exists(tile_dir):
                logger.debug('create tile directory: %s', tile_dir)
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

    @cached_property
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

    @cached_property
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
            logger.debug('determine tile files for level %d', i)
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


class ObjectLayer(Layer):

    __metaclass__ = ABCMeta

    '''
    Abstract base class for object layers, which provide map coordinates for
    objects for vector-graphic based visualization in `TissueMAPS`.
    '''

    def __init__(self, experiment, name,
                 image_displacement=0, well_spacer_size=500):
        '''
        Initialize an object of class ObjectLayer.

        Parameters
        ----------
        experiment: tmlib.experiment.Experiment
            configured experiment object
        name: str
            name of the layer (objects)
        image_displacement: int, optional
            displacement in x, y direction in pixels between individual images;
            useful to account for an overlap between images (default: ``0``)
        well_spacer_size: int, optional
            number of pixels that should be introduced between wells
            (default: ``500``)

        Warning
        -------
        The values for `well_spacer_size` and `image_displacement`
        must be the same as for the other layers,
        otherwise objects and images will not align.
        '''
        super(ObjectLayer, self).__init__(
                experiment, image_displacement, well_spacer_size)
        self.name = name

    @abstractmethod
    def create(self):
        pass


class SegmentedObjectLayer(Layer):

    '''
    Class for creation of a layer of segmented objects, such as "cells".
    The coordinates of the object outlines (simplified polygons) are
    calculated based existing segmentations. They are stored together with the
    corresponding extracted features in a HDF5 file.
    '''

    def __init__(self, experiment, name,
                 image_displacement=0, well_spacer_size=500):
        '''
        Initialize an object of class SegmentedObjectLayer.

        Parameters
        ----------
        experiment: tmlib.experiment.Experiment
            configured experiment object
        name: str
            name of the layer (objects)
        image_displacement: int, optional
            displacement in x, y direction in pixels between individual images;
            useful to account for an overlap between images (default: ``0``)
        well_spacer_size: int, optional
            number of pixels that should be introduced between wells
            (default: ``500``)

        Warning
        -------
        The values for `well_spacer_size` and `image_displacement`
        must be the same as for the other layers,
        otherwise objects and images will not align.
        '''
        super(SegmentedObjectLayer, self).__init__(
                experiment, image_displacement, well_spacer_size)
        self.name = name

    def create(self, data_files, align=False, tolerance=1):
        '''
        Determine the coordinates of simplified object contours (polygons with
        reduced number of points) and write them to the HDF5 data file:
        The *y*, *x* coordinates of each object will be stored in a
        separate dataset of shape (n, 2), where n is the number of points
        on the perimeter sorted in counter-clockwise order.
        The first column of the dataset contains the *x* coordinate and the
        second column the inverted *y* coordinate as required by
        `Openlayers <http://openlayers.org/>`.
        The name of the dataset is the global ID of the object, which
        corresponds to the row index of the object in the `features`
        dataset.

        Within the file the datasets are located in the subgroup "coordinates":
        ``/objects/<object_name>/map_data/coordinates/<object_id>``.

        Also join features datasets across individual `data_files` and write
        each feature dataset containing values for all objects into a separate
        dataset. The object ID can be used as an index.

        Within the file the datasets are located in the subgroup "features":
        ``/objects/<object_name>/features/<feature_name>``.

        Parameters
        ----------
        data_files: List[str]
            absolute path to individual data files
        align: bool, optional
            whether images should be aligned between cycles
            (default: ``False``)
        tolerance: float, optional
            accuracy of polygon approximation; the larger the value the less
            accurate the polygon will be approximated, i.e. the less coordinate
            values will be used to describe its contour; if ``0`` the original
            contour is used (default: ``1``)
        '''
        filename = os.path.join(self.experiment.dir, self.experiment.data_file)
        with DatasetWriter(filename) as store:
            obj_path = '/objects/%s' % self.name
            store.create_group(obj_path)
            store.set_attribute(obj_path, 'visual_type', 'polygon')
            segm_path = '%s/segmentation' % obj_path
            outline_coord_path = '%s/map_data/outlines/coordinates' % obj_path
            centroid_coord_path = '%s/map_data/centroids/coordinates' % obj_path
            global_obj_id = 0
            for j, f in enumerate(data_files):
                with DatasetReader(f) as data:

                    logger.debug('process data in file "%s"', f)
                    logger.debug('calculate object outline coordinates')

                    # Get the indices of objects at the border of images
                    # (using the parent objects as references)
                    if 'parent_name' in data.list_datasets(segm_path):
                        parent = data.read('%s/parent_name' % segm_path)
                        p_segm_path = '/objects/%s/segmentation' % parent
                        is_border = data.read('%s/is_border' % p_segm_path).astype(bool)
                        if j == 0:
                            # Store the relation between objects
                            store.write('%s/parent_name' % segm_path, parent)
                            # TODO: how to relate global "parent_object_ids"???
                    else:
                        is_border = data.read('%s/is_border' % segm_path).astype(bool)

                    # A jterator job represents a unique image acquisition site.
                    # We have to identify the position of each site within the
                    # overall acquisition grid and update the outline coordinates
                    # accordingly, i.e. translate site-specific coordinates into
                    # global ones.

                    plate_index = data.read('/metadata/plate_index')
                    plate = self.experiment.plates[plate_index]
                    well_name = data.read('/metadata/well_name')
                    plate_coords = plate.map_well_id_to_coordinate(well_name)
                    well_coords = (
                        data.read('/metadata/well_position/y'),
                        data.read('/metadata/well_position/x')
                    )
                    logger.debug('plate # %d', plate_index)
                    logger.debug('well position within plate: {0}'.format(
                                    plate_coords))
                    logger.debug('well name: %s', well_name)
                    logger.debug('image position within well: {0}'.format(
                                    well_coords))

                    n_prior_well_rows = plate.nonempty_row_indices.index(
                                                plate_coords[0])
                    n_prior_well_cols = plate.nonempty_column_indices.index(
                                                plate_coords[1])
                    n_prior_wells = (n_prior_well_rows, n_prior_well_cols)

                    y_offset, x_offset = self._calc_global_offset(
                                                p, well_coords, n_prior_wells)

                    if align:
                        # Images may need to be aligned between cycles
                        shift_offset_y = data.read('/metadata/shift_offset/y')
                        shift_offset_x = data.read('/metadata/shift_offset/x')
                        y_offset += shift_offset_y
                        x_offset += shift_offset_x

                    logger.debug('offset for site %d: y %d - x %d',
                                 j, y_offset, x_offset)

                    coords_y = data.read('%s/coordinates/y' % segm_path)
                    coords_x = data.read('%s/coordinates/x' % segm_path)
                    centroids_y = data.read('%s/centroids/y' % segm_path)
                    centroids_x = data.read('%s/centroids/x' % segm_path)
                    object_ids = data.read('%s/ids' % segm_path)
                    for i, obj_id in enumerate(object_ids):
                        # Reduce the number of outline points to reduce the
                        # data that we have to send to the client and render
                        contour = np.array([coords_y[i], coords_x[i]]).T
                        poly = skimage.measure.approximate_polygon(
                                        contour, tolerance).astype(int)

                        # Add offset to coordinates to account for position of
                        # the object within the total well plate overview.
                        # Openlayers wants the x coordinate in the first
                        # column and the inverted y coordinate in the second.
                        outline_coordinates = pd.DataFrame({
                            'y': -1 * (poly[:, 0] + y_offset),
                            'x': poly[:, 1] + x_offset
                        })
                        o_path = '%s/%d' % (outline_coord_path, global_obj_id)
                        store.write(o_path, outline_coordinates)
                        store.set_attribute(o_path, 'columns', ['x', 'y'])
                        centroid_coordinates = pd.Series({
                            'y': -1 * (centroids_y[i] + y_offset),
                            'x': centroids_x[i] + x_offset
                        })
                        c_path = '%s/%d' % (centroid_coord_path, global_obj_id)
                        store.write(c_path, centroid_coordinates)
                        store.set_attribute(c_path, 'columns', ['x', 'y'])

                        # Store the position of the corresponding image
                        # within the well
                        store.append('%s/metadata/well_position_y' % obj_path,
                                     [well_coords[0]])
                        store.append('%s/metadata/well_position_x' % obj_path,
                                     [well_coords[1]])
                        global_obj_id += 1

                    logger.debug('add segmentations to datasets')
                    job_id = data.read('/metadata/job_id')
                    job_path = '%s/%d' % (segm_path, job_id)
                    store.append('%s/coordinates/y' % job_path, coords_y)
                    store.append('%s/coordinates/x' % job_path, coords_x)
                    # The "is_border" vector indicates whether the parent (!)
                    # object lies at the border of the image.
                    store.append('%s/is_border' % obj_path, is_border)

                    # Store the name of the corresponding plate and well
                    plates = np.repeat(plate_index, len(object_ids))
                    store.append('%s/metadata/plate_index' % obj_path, plates)
                    wells = np.repeat(well_name, len(object_ids))
                    store.append('%s/metadata/well_name' % obj_path, wells)

            # Store objects ids separately as a sorted array of integers
            store.write('%s/ids' % obj_path, range(global_obj_id))


class WellObjectLayer(Layer):

    '''
    Class for creation of a layer of *well* objects.
    The coordinates of the well outlines (rectangular polygons) are derived
    from the image metadata. They are stored in a HDF5 file.
    '''

    def __init__(self, experiment, name='wells',
                 image_displacement=0, well_spacer_size=500):
        '''
        Initialize an object of class WellObjectLayer.

        Parameters
        ----------
        experiment: tmlib.experiment.Experiment
            configured experiment object
        name: str, optional
            name of the layer (default: ``"wells"``)
        image_displacement: int, optional
            displacement in x, y direction in pixels between individual images;
            useful to account for an overlap between images (default: ``0``)
        well_spacer_size: int, optional
            number of pixels that should be introduced between wells
            (default: ``500``)

        Warning
        -------
        The values for `well_spacer_size` and `image_displacement`
        must be the same as for the other layers,
        otherwise objects and images will not align.
        '''
        super(WellObjectLayer, self).__init__(
                experiment, image_displacement, well_spacer_size)
        self.name = name

    def create(self):
        '''
        Determine the coordinates of the object contours (rectangular polygons
        so the 4 extrema points are sufficient) and write them to the HDF5 data
        file:
        The *y*, *x* coordinates of each object will be stored in a
        separate dataset of shape (4, 2), sorted in counter-clockwise order.
        The first column of the dataset contains the *x* coordinate and the
        second column the inverted *y* coordinate as required by
        `Openlayers <http://openlayers.org/>`.
        The name of the dataset is the global ID of the object, which
        corresponds to the row index of the object in the `features`
        dataset.

        Within the file the datasets are located in the subgroup "coordinates":
        ``/objects/wells/map_data/coordinates/<object_id>``.

        Also calculate per well statistics (such as mean and standard deviation)
        for each feature of segmented objects and store them as separate
        datasets. The well ID can be used as an index.

        Within the file the datasets are located in the subgroup "features":
        ``/objects/wells/features/<feature_name>``.
        '''
        filename = os.path.join(self.experiment.dir, self.experiment.data_file)
        with DatasetReader(filename) as data:
            objects = data.list_groups('/objects')
            if 'wells' in objects:
                objects.remove('wells')
            feat_path = dict()
            plate_ref = dict()
            well_ref = dict()
            for obj in objects:
                obj_path = '/objects/%s' % obj
                feat_path[obj] = '%s/features' % obj_path
                # NOTE: This assumes that the layers for segmented objects
                # have already been created
                plate_ref[obj] = data.read('%s/metadata/plate_index' % obj_path)
                well_ref[obj] = data.read('%s/metadata/well_name' % obj_path)

            with DatasetWriter(filename) as store:
                obj_path = '/objects/%s' % self.name
                store.create_group(obj_path)
                store.set_attribute(obj_path, 'visual_type', 'polygon')
                outline_coord_path = '%s/map_data/outlines/coordinates' % obj_path
                centroid_coord_path = '%s/map_data/centroids/coordinates' % obj_path
                global_obj_id = 0  # global: across different plates
                ids = list()
                for p, plate in enumerate(self.experiment.plates):
                    logger.debug('process wells of plate "%s"', plate.name)
                    image_metadata = plate.cycles[0].image_metadata
                    wells = np.unique(image_metadata.well_name)
                    for well_name in wells:
                        logger.debug('process well "%s"', well_name)
                        logger.debug('calculate object outline coordinates')
                        plate_coords = plate.map_well_id_to_coordinate(well_name)
                        n_prior_well_rows = plate.nonempty_row_indices.index(
                                                    plate_coords[0])
                        n_prior_well_cols = plate.nonempty_column_indices.index(
                                                    plate_coords[1])
                        n_prior_wells = (n_prior_well_rows, n_prior_well_cols)

                        # Calculate coordinates of extrema points
                        # NOTE: Openlayers wants the x coordinate in the first
                        # column and the inverted y coordinate in the second.
                        y_max = np.max(image_metadata.well_position_y)
                        x_max = np.max(image_metadata.well_position_x)
                        y_add = self.image_dimensions[0] - self.image_displacement
                        x_add = self.image_dimensions[1] - self.image_displacement
                        # top left
                        y_offset, x_offset = self._calc_global_offset(
                                                p, (0, 0), n_prior_wells)
                        top_left_coordinate = (x_offset, -y_offset)

                        # top right
                        y_offset, x_offset = self._calc_global_offset(
                                                p, (0, x_max), n_prior_wells)
                        x_offset += x_add
                        top_right_coordinate = (x_offset, -y_offset)

                        # lower left
                        y_offset, x_offset = self._calc_global_offset(
                                                p, (y_max, 0), n_prior_wells)
                        y_offset += y_add
                        lower_left_coordinate = (x_offset, -y_offset)

                        # lower right
                        y_offset, unused = self._calc_global_offset(
                                                p, (y_max, 0), n_prior_wells)
                        y_offset += y_add
                        unused, x_offset = self._calc_global_offset(
                                                p, (0, x_max), n_prior_wells)
                        x_offset += x_add
                        lower_right_coordinate = (x_offset, -y_offset)

                        # sort them counter-clockwise
                        outline_coordinates = np.array([
                            top_right_coordinate,
                            top_left_coordinate,
                            lower_left_coordinate,
                            lower_right_coordinate,
                            top_right_coordinate
                        ])
                        centroid_coordinates = (
                            int(np.mean(outline_coordinates[:, 0])),
                            int(np.mean(outline_coordinates[:, 1]))
                        )
                        o_path = '%s/%s' % (outline_coord_path, global_obj_id)
                        c_path = '%s/%s' % (centroid_coord_path, global_obj_id)
                        # TODO: do this smarter by avoiding the whole
                            # processing in the first place
                        if not store.exists(o_path):
                            store.write(o_path, outline_coordinates)
                            store.set_attribute(o_path, 'columns', ['x', 'y'])
                        if not store.exists(c_path):
                            store.write(c_path, centroid_coordinates)
                            store.set_attribute(o_path, 'columns', ['x', 'y'])

                        # Pre-calculate per-well statistics for features of
                        # children objects (e.g. "cells")
                        logger.debug('calculate statistics for children '
                                     'object features')
                        for obj in objects:
                            index = (
                                (well_ref[obj] == well_name) &
                                (plate_ref[obj] == plate.index)
                            )
                            # Adhere to structure of SegmentedObjectLayer, i.e.
                            # object id can be used as index for feature
                            # datasets
                            w_path = '%s/features' % obj_path
                            store.create_group(w_path)
                            o_path = '%s/%s_Count' % (w_path, obj)
                            store.append(o_path, [np.sum(index)])
                            if data.exists(feat_path[obj]):
                                features = data.list_datasets(feat_path[obj])
                                for f in features:
                                    f_path = '%s/%s' % (feat_path[obj], f)
                                    # Only load relevant objects
                                    feat_data = data.read(f_path, index=index)
                                    store.append(
                                        '%s/%s_Mean' % (w_path, f),
                                        [np.nanmean(feat_data)])
                                    store.append(
                                        '%s/%s_Std' % (w_path, f),
                                        [np.nanstd(feat_data)])
                                    store.append(
                                        '%s/%s_Min' % (w_path, f),
                                        [np.nanmin(feat_data)])
                                    store.append(
                                        '%s/%s_Max' % (w_path, f),
                                        [np.nanmax(feat_data)])
                        ids.append(global_obj_id)
                        global_obj_id += 1

                store.write('%s/ids' % obj_path, range(global_obj_id))
