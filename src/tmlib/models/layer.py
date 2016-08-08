import os
import re
import numpy as np
import logging
import lxml
import itertools
import collections
from cached_property import cached_property
from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import Session
from sqlalchemy.orm import relationship, backref
from sqlalchemy import UniqueConstraint
from sqlalchemy.ext.hybrid import hybrid_property

from tmlib.models.file import ChannelImageFile
from tmlib.models.site import Site
from tmlib.models.well import Well
from tmlib.models.plate import Plate
from tmlib.models.base import Model
from tmlib.models import distribute_by_replication
from tmlib.utils import autocreate_directory_property
from tmlib.models.utils import remove_location_upon_delete
from tmlib.writers import XmlWriter
from tmlib.errors import RegexError
from tmlib.image import PyramidTile

logger = logging.getLogger(__name__)

#: Format string for channel layer locations
CHANNEL_LAYER_LOCATION_FORMAT = 'layer_{id}'


@remove_location_upon_delete
@distribute_by_replication
class ChannelLayer(Model):

    '''A *channel layer* represents a multi-resolution overview of all images
    belonging to a given *channel*, *z-plane* and *time point*.
    as a pyramid in `Zoomify <http://www.zoomify.com/>`_ format.

    Attributes
    ----------
    tpoint: int
        zero-based time series index
    zplane: int
        zero-based z-resolution index
    height: int
        number of pixels along the vertical axis
    width: int
        number of pixels along the horizontal axis
    max_intensity: int
        maximum intensity value at which channel images were clipped
        at the original bit depth
    min_intensity: int
        minimum intensity value at which channel images were clipped at
        original bit depth
    channel_id: int
        ID of the parent channel
    channel: tmlib.models.Channel
        parent channel to which the plate belongs
    '''

    #: str: name of the corresponding database table
    __tablename__ = 'channel_layers'

    __table_args__ = (UniqueConstraint('zplane', 'tpoint', 'channel_id'), )

    # Table columns
    zplane = Column(Integer, index=True)
    tpoint = Column(Integer, index=True)
    _height = Column('height', Integer)
    _width = Column('width', Integer)
    max_intensity = Column(Integer)
    min_intensity = Column(Integer)
    channel_id = Column(
        Integer,
        ForeignKey('channels.id', onupdate='CASCADE', ondelete='CASCADE'),
        index=True
    )

    # Relationships to other tables
    channel = relationship(
        'Channel',
        backref=backref('layers', cascade='all, delete-orphan')
    )

    def __init__(self, tpoint, zplane, channel_id):
        '''
        Parameters
        ----------
        tpoint: int
            zero-based time series index
        zplane: int
            zero-based z-resolution index
        channel_id: int
            ID of the parent channel
        '''
        self.tpoint = tpoint
        self.zplane = zplane
        self.channel_id = channel_id
        self._height = None
        self._width = None

    @hybrid_property
    def height(self):
        '''int: number of pixels along vertical axis at highest resolution level
        '''
        if self._height is None:
            self._height = self._maxzoom_image_size[0]
        return self._height

    @hybrid_property
    def width(self):
        '''int: number of pixels along horizontal axis at highest resolution
        level
        '''
        if self._width is None:
            self._width = self._maxzoom_image_size[1]
        return self._width

    @property
    def tile_size(self):
        '''int: maximal number of pixels along an axis of a tile
        '''
        return 256

    @property
    def zoom_factor(self):
        '''int: factor by which resolution increases per pyramid level'''
        return self.channel.experiment.zoom_factor

    @autocreate_directory_property
    def location(self):
        '''str: location were the channel layer content is stored'''
        if self.id is None:
            raise AttributeError(
                'Channel layer "%s" doesn\'t have an entry in the database yet. '
                'Therefore, its location cannot be determined.' % self.name
            )
        return os.path.join(
            self.channel.layers_location,
            CHANNEL_LAYER_LOCATION_FORMAT.format(id=self.id)
        )

    @property
    def n_levels(self):
        '''int: number of zoom levels'''
        return len(self.dimensions)

    @property
    def n_tiles(self):
        '''int: total number of tiles across all resolution levels'''
        return np.sum([np.prod(dims) for dims in self.dimensions])

    @property
    def n_tile_groups(self):
        '''int: number of tile groups'''
        return int(np.ceil(np.float(self.n_tiles) / 256))

    @property
    def maxzoom_level_index(self):
        '''int: index of the highest resolution level, i.e. the base of the
        pyramid
        '''
        return len(self.dimensions) - 1

    @cached_property
    def dimensions(self):
        '''List[Tuple[int]]: number of tiles along the vertical and horizontal
        axis of the layer at each zoom level; levels are sorted such that the
        first element represents the lowest resolution (maximally zoomed out)
        level and the last element the highest resolution (maximally zoomed in)
        level
        '''
        # NOTE: This could also be calculated based on maxzoom_level only
        logger.debug('calculate layer dimensions')
        levels = list()
        for i, (height, width) in enumerate(self.image_size):
            n_rows = int(np.ceil(np.float(height) / np.float(self.tile_size)))
            n_cols = int(np.ceil(np.float(width) / np.float(self.tile_size)))
            levels.append((n_rows, n_cols))
        return levels

    @cached_property
    def _maxzoom_image_size(self):
        '''Determines the size of the image at the highest resolution level,
        i.e. at the base of the pyramid.
        '''
        logger.debug('calculate size of image at highest resolution level')
        experiment = self.channel.experiment
        plate_sizes = np.array([p.image_size for p in experiment.plates])
        # TODO: This can cause problems when wells were deleted (because
        # metadata configuration was resubmitted), but channels still exist
        if not(len(np.unique(plate_sizes[:, 0])) == 1 and
                len(np.unique(plate_sizes[:, 1]) == 1)):
            logger.warning('plates don\'t have equal sizes')
        # Take the size of the plate which contains the most wells. The
        # other plates should then be filled with empty tiles.
        plate_size = (np.max(plate_sizes[:, 0]), np.max(plate_sizes[:, 1]))
        # Introduce spacers between plates
        row_spacer_height = (
            (experiment.plate_grid.shape[0] - 1) *
            experiment.plate_spacer_size
        )
        column_spacer_width = (
            (experiment.plate_grid.shape[1] - 1) *
            experiment.plate_spacer_size
        )
        return tuple(
            np.array(plate_size) * experiment.plate_grid.shape +
            np.array([row_spacer_height, column_spacer_width])
        )

    @cached_property
    def image_size(self):
        '''List[Tuple[int]]: number of pixels along the vertical and horizontal
        axis of the layer at each zoom level; levels are sorted such that the
        first element represents the lowest resolution (maximally zoomed out)
        level and the last element the highest resolution (maximally zoomed in)
        level
        '''
        logger.debug('calculate image size at each resolution level')
        experiment = self.channel.experiment
        levels = list()
        height, width = self.height, self.width
        levels.append((height, width))
        # Determine the size of the images at lower resolution levels up to the
        # top of the pyramid
        while True:
            height = int(np.ceil(np.float(height) / experiment.zoom_factor))
            width = int(np.ceil(np.float(width) / experiment.zoom_factor))
            levels.append((height, width))
            if height <= self.tile_size and width <= self.tile_size:
                break
        # Sort zoom levels top-down, i.e. from lowest to highest resolution
        return list(reversed(levels))

    def _calc_tile_indices_and_offsets(self, position, length, displacement):
        '''Calculates index (row or column) and pixel offset for each tile
        that falls within a given image along a given axis (either vertical
        or horizontal).

        Parameters
        ----------
        position: int
            pixel position of the top, left corner of the image in the layer
            on the given axis
        length: int
            length of the image in pixels along the given axis
        displacement: int
            displacement of the image to its neighboring image in pixels
            along the given axis

        Returns
        -------
        Dict[str, List[int]]
            indices and offsets of tiles falling within the given image axis
        '''
        start_fraction = (
            np.float(position) / np.float(self.tile_size)
        )
        start_index = int(np.floor(start_fraction))
        start_diff = start_index - start_fraction
        start_offset = int(self.tile_size * start_diff)

        end_fraction = (
            np.float(position + length - displacement) /
            np.float(self.tile_size)
        )
        end_index = int(np.ceil(end_fraction))
        end_diff = end_index - end_fraction
        end_offset = int(self.tile_size * end_diff)

        indices = range(start_index, end_index)

        return {
            'indices': indices,
            'offsets': [
                start_offset + i * self.tile_size
                if i < len(indices)
                else end_offset
                for i in xrange(len(indices))
            ]
        }

    def map_image_to_base_tiles(self, image_file):
        '''Maps an image to the corresponding tiles at the base of the pyramid
        (maximal zoom level) that intersect with the image.

        Parameters
        ----------
        image_file: tmlib.models.ChannelImageFile

        Returns
        -------
        List[Dict[str, Tuple[int]]]
            array of mappings with "row" and "column" coordinate as well as
            "y_offset" and "x_offset" relative to `image_file` for each tile
            whose pixels are part of `image_file`

        Note
        ----
        For those tiles that overlap multiple images, only map those at the
        upper and/or left border of the image in `image_file`
        '''
        mappings = list()
        experiment = self.channel.experiment
        site = image_file.site
        well = image_file.site.well
        y_offset_site, x_offset_site = site.offset
        # Determine the index and offset of each tile whose pixels are part of
        # the image
        row_info = self._calc_tile_indices_and_offsets(
            y_offset_site, site.image_size[0],
            experiment.vertical_site_displacement
        )
        col_info = self._calc_tile_indices_and_offsets(
            x_offset_site, site.image_size[1],
            experiment.horizontal_site_displacement
        )
        # Each job processes only the overlapping tiles at the upper and/or
        # left border of the image. This prevents that tiles are created twice,
        # which could cause problems with file locking and so on.
        # Images at the lower and/or right border of the total overview, wells,
        # or plates represent an exception because in these cases there is
        # no neighboring image to create the tile instead, but an empty spacer.
        # The same is true in case of missing neighboring images.
        session = Session.object_session(self)
        lower_neighbor_count = session.query(ChannelImageFile.id).\
            join(Site).\
            filter(
                Site.y == site.y + 1, Site.x == site.x,
                Site.well_id == site.well_id,
                ChannelImageFile.channel_id == self.channel_id,
                ChannelImageFile.tpoint == self.tpoint
            ).\
            count()
        right_neighbor_count = session.query(ChannelImageFile.id).\
            join(Site).\
            filter(
                Site.y == site.y, Site.x == site.x + 1,
                Site.well_id == site.well_id,
                ChannelImageFile.channel_id == self.channel_id,
                ChannelImageFile.tpoint == self.tpoint
            ).\
            count()
        has_lower_neighbor = lower_neighbor_count > 0
        has_right_neighbor = right_neighbor_count > 0
        for i, row in enumerate(row_info['indices']):
            y_offset = row_info['offsets'][i]
            is_overhanging_vertically = (
                (y_offset + self.tile_size) > site.image_size[0]
            )
            is_not_lower_plate_border = (row + 1) != self.dimensions[-1][0]
            is_not_lower_well_border = (site.y + 1) != well.dimensions[0]
            if is_overhanging_vertically and has_lower_neighbor:
                if (is_not_lower_plate_border and
                        is_not_lower_well_border):
                    continue
            for j, col in enumerate(col_info['indices']):
                x_offset = col_info['offsets'][j]
                is_overhanging_horizontally = (
                    (x_offset + self.tile_size) > site.image_size[1]
                )
                is_not_right_plate_border = (col + 1) != self.dimensions[-1][1]
                is_not_right_well_border = (site.x + 1) != well.dimensions[1]
                if is_overhanging_horizontally and has_right_neighbor:
                    if (is_not_right_plate_border and
                            is_not_right_well_border):
                        continue
                mappings.append({
                    'row': row,
                    'column': col,
                    'y_offset': y_offset,
                    'x_offset': x_offset
                })
        return mappings

    def get_empty_base_tile_coordinates(self):
        '''Gets coordinates of empty base tiles, i.e. tiles at the maximum
        zoom level that don't map to an image because they fall into
        a spacer region, e.g. gap introduced wells.

        Returns
        -------
        Set[Tuple[int]]
            row, column coordinates
        '''
        logger.debug('get coordinates of empty tiles at maxzoom level')
        tile_coords = self.base_tile_coordinate_to_image_file_map.keys()
        rows = range(self.dimensions[-1][0])
        cols = range(self.dimensions[-1][1])
        all_tile_coords = list(itertools.product(rows, cols))
        return set(all_tile_coords) - set(tile_coords)

    def _calc_tile_indices(self, position, length, displacement):
        '''Calculates row or column index for each tile
        that maps to either the vertical or horizontal axis of the given image,
        respectively.

        Parameters
        ----------
        position: int
            pixel position of the top, left corner of the image in the layer
            on the given axis
        length: int
            length of the image in pixels along the given axis
        displacement: int
            displacement of the image to its neighboring image in pixels
            along the given axis

        Returns
        -------
        List[int]
            indices of tiles that map to the given axis
        '''
        start_fraction = (
            np.float(position) /
            np.float(self.tile_size)
        )
        start_index = int(np.floor(start_fraction))

        end_fraction = (
            np.float(position + length - displacement) /
            np.float(self.tile_size)
        )
        end_index = int(np.ceil(end_fraction))

        return range(start_index, end_index)

    def map_base_tile_to_images(self, site):
        '''Maps tile coordinates to image files intersecting with the tile.

        Parameters
        ----------
        site: tmlib.models.Site
            site whose neighbours could be included in the search

        Returns
        -------
        Dict[Tuple[int], List[int]]
            IDs of all images, which intersect with a given tile at the
            maximal zoom level
        '''
        experiment = self.channel.experiment
        session = Session.object_session(self)
        neighbouring_sites = session.query(Site).\
            join(Well).\
            filter(
                Well.id == site.well.id,
                Site.x.in_([site.x - 1, site.x]),
                Site.y.in_([site.y - 1, site.y])
            )

        mapping = collections.defaultdict(list)
        for current_site in neighbouring_sites:
            if current_site.y == site.y and current_site.x == site.x:
                continue
            if current_site.omitted:
                continue
            fid = session.query(ChannelImageFile.id).\
                filter_by(site_id=current_site.id, channel_id=self.channel.id).\
                one()[0]
            y_offset_site, x_offset_site = current_site.offset
            row_indices = self._calc_tile_indices(
                y_offset_site, current_site.image_size[0],
                experiment.vertical_site_displacement
            )
            col_indices = self._calc_tile_indices(
                x_offset_site, current_site.image_size[1],
                experiment.horizontal_site_displacement
            )
            for row, col in itertools.product(row_indices, col_indices):
                mapping[(row, col)].append(fid)

        return mapping

    @cached_property
    def base_tile_coordinate_to_image_file_map(self):
        '''Dict[Tuple[int], List[int]]: IDs of all images, which intersect
        with a given tile; maps coordinates of tiles at the maximal zoom level
        to the files of intersecting images
        '''
        logger.debug('create mapping of base tile coordinates to image files')
        experiment = self.channel.experiment
        session = Session.object_session(self)
        sites = session.query(Site).\
            join(Well).\
            join(Plate).\
            filter(Plate.experiment_id == experiment.id)
        mapping = collections.defaultdict(list)
        for site in sites:
            if site.omitted:
                continue
            fid = session.query(ChannelImageFile.id).\
                filter_by(site_id=site.id, channel_id=self.channel.id).\
                one()[0]
            y_offset_site, x_offset_site = site.offset
            row_indices = self._calc_tile_indices(
                y_offset_site, site.image_size[0],
                experiment.vertical_site_displacement
            )
            col_indices = self._calc_tile_indices(
                x_offset_site, site.image_size[1],
                experiment.horizontal_site_displacement
            )
            for row, col in itertools.product(row_indices, col_indices):
                mapping[(row, col)].append(fid)
        return mapping

    def calc_coordinates_of_next_higher_level(self, level, row, column):
        '''Calculates for a given tile the coordinates of the 4 tiles at the
        next higher zoom level that represent the tile at the current level.

        Parameters
        ----------
        level: int
            zero-based index of the current zoom level
        row: int
            zero-based index of the current row
        column: int
            zero-based index of the current column

        Returns
        -------
        List[Tuple[int]]
            row, column coordinate at the next higher zoom level
        '''
        coordinates = list()
        experiment = self.channel.experiment
        max_row, max_column = self.dimensions[level+1]
        rows = range(
            row * experiment.zoom_factor,
            (row * experiment.zoom_factor + experiment.zoom_factor - 1) + 1
        )
        cols = range(
            column * experiment.zoom_factor,
            (column * experiment.zoom_factor + experiment.zoom_factor - 1) + 1
        )
        for r, c in itertools.product(rows, cols):
            if r < max_row and c < max_column:
                coordinates.append((r, c))
        return coordinates

    @cached_property
    def tile_coordinate_group_map(self):
        '''Dict[Tuple[int], int]: mapping of tile coordinate
        (level, row, and column index) to tile group index
        '''
        logger.debug('build mapping of tile coordinates to group index')
        n = 0
        mapping = dict()
        for level, dims in enumerate(self.dimensions):
            rows, cols = dims
            for r, c in itertools.product(np.arange(rows), np.arange(cols)):
                # Each tile group directory holds maximally 256 files and
                # groups are filled up from top to bottom, starting at 0 for
                # the most zoomed out tile and then increasing monotonically
                # in a row wise manner
                group_index = n // 256
                mapping[(level, r, c)] = group_index
                n += 1
        return mapping

    def create_image_properties_file(self):
        '''Creates the image properties XML file, which provides
        meta-information about the pyramid, such as the image dimensions at the
        highest resolution level and the total number of tiles.
        '''
        logger.debug('create image properties xml file')
        xml = lxml.etree.Element(
            'IMAGE_PROPERTIES',
            WIDTH=str(self.image_size[-1][1]),
            HEIGHT=str(self.image_size[-1][0]),
            NUMTILES=str(self.n_tiles),
            NUMIMAGES=str(1),
            VERSION='1.8',
            TILESIZE=str(self.tile_size)
        )
        filename = os.path.join(self.location, 'ImageProperties.xml')
        with XmlWriter(filename) as f:
            f.write(xml)

    @staticmethod
    def build_tile_group_name(i):
        '''Builds name of the `i`-th tile group.

        Parameters
        ----------
        i: int
            zero-based tile group index

        Returns
        -------
        str
            tile group folder name
        '''
        return 'TileGroup{i}'.format(i=i)

    @staticmethod
    def build_tile_file_name(level, row, col):
        '''Builds name for a tile file at a given pyramid position.

        Parameters
        ----------
        level: int
            zero-based zoom level index
        row: int
            zero-based row index of the tile at the given zoom `level`
        col: int
            zero-based column index of the tile at the given zoom `level`

        Returns
        -------
        str
            name of the tile
        '''
        return '{level}-{col}-{row}.jpg'.format(level=level, col=col, row=row)

    def get_coordinate_from_name(self, filename):
        '''Determines "level", "row", and "column" index of a tile from its
        filename.

        Parameters
        ----------
        filename: str
            name of a tile file

        Returns
        -------
        Tuple[int]
            zero-based *level*, *row*, and *column* index of the given tile

        Raises
        ------
        tmlib.errors.RegexError
            when indices cannot be determined from filename
        '''
        r = re.compile('(?P<level>\d+)-(?P<column>\d+)-(?P<row>\d+).jpg')
        m = r.search(filename).groupdict()
        if not m:
            RegexError(
                'Indices could not be determined from file: %s'
                % filename
            )
        indices = {k: int(v) for k, v in m.iteritems()}
        return (indices['level'], indices['row'], indices['column'])

    def create_tile_groups(self):
        '''Creates all required tile group directories.

        Raises
        ------
        OSError
            when a tile group directory already exists
        '''
        for i in range(self.n_tile_groups):
            tile_group_dir = os.path.join(self.location, 'TileGroup%d' % i)
            if not os.path.exists(tile_group_dir):
                logger.debug('create tile directory: %s', tile_group_dir)
                os.mkdir(tile_group_dir)

    def get_coordinates_of_next_higher_level(self, filename):
        '''Gets tiles of the next higher resolution level that make up the given
        tile.

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
        level, row, col = self.get_coordinate_from_name(filename)
        return self.calc_coordinates_of_next_higher_level(level, row, col)

    def extract_tile_from_image(self, image, y_offset, x_offset):
        '''Extracts a subset of pixels for a tile from an image. In case the
        area of the tile overlaps the image, pad the tile with zeros.

        Parameters
        ----------
        image: tmlib.image.ChannelImage
            image from which the tile should be extracted
        y_offset: int
            offset along the vertical axis of `image`
        x_offset: int
            offset along the horizontal axis of `image`

        Returns
        -------
        tmlib.image.PyramidTile
            extracted tile

        Note
        ----
        The size of the tile is predefined.
        '''
        # Some tiles may lie on the border of wells and contain spacer
        # background pixels. The pixel offset is negative in these cases and
        # missing pixels are replaced with zeros.
        y_end = y_offset + self.tile_size
        x_end = x_offset + self.tile_size

        n_top = None
        n_bottom = None
        n_left = None
        n_right = None
        if y_offset < 0:
            n_top = abs(y_offset)
            y_offset = 0
        elif (image.dimensions[0] - y_offset) < self.tile_size:
            n_bottom = self.tile_size - (image.dimensions[0] - y_offset)
        if x_offset < 0:
            n_left = abs(x_offset)
            x_offset = 0
        elif (image.dimensions[1] - x_offset) < self.tile_size:
            n_right = self.tile_size - (image.dimensions[1] - x_offset)

        extracted_pixels = image.extract(
            y_offset, y_end-y_offset, x_offset, x_end-x_offset
        ).array
        tile = PyramidTile(extracted_pixels)
        if n_top is not None:
            tile = tile.pad_with_background(n_top, 'top')
        if n_bottom is not None:
            tile = tile.pad_with_background(n_bottom, 'bottom')
        if n_left is not None:
            tile = tile.pad_with_background(n_left, 'left')
        if n_right is not None:
            tile = tile.pad_with_background(n_right, 'right')

        return tile

    def as_dict(self):
        '''Returns attributes as key-value pairs.

        Returns
        -------
        dict
        '''
        image_height, image_width = self.image_size[-1]
        return {
            'id': self.hash,
            'tpoint': self.tpoint,
            'zplane': self.zplane,
            'image_size': {
                'width': image_width,
                'height': image_height
            }
        }

    def __repr__(self):
        return (
            '<%s(id=%r, channel=%r, tpoint=%r, zplane=%r)>'
            % (self.__class__.__name__, self.id, self.channel.index,
                self.tpoint, self.zplane)
        )
