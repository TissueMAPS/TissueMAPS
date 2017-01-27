# TmLibrary - TissueMAPS library for distibuted image analysis routines.
# Copyright (C) 2016  Markus D. Herrmann, University of Zurich and Robin Hafen
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
import os
import re
import numpy as np
import logging
import lxml
import itertools
import collections
from cached_property import cached_property
from sqlalchemy import Column, Integer, ForeignKey, String, UniqueConstraint
from sqlalchemy import or_
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import relationship, backref, Session
from sqlalchemy.ext.hybrid import hybrid_property

from tmlib.models.file import ChannelImageFile
from tmlib.models.site import Site
from tmlib.models.well import Well
from tmlib.models.feature import FeatureValues
from tmlib.models.result import LabelValues
from tmlib.models.tile import ChannelLayerTile
from tmlib.models.mapobject import MapobjectSegmentation
from tmlib.models.plate import Plate
from tmlib.models.base import ExperimentModel
from tmlib.models.utils import ExperimentConnection, ExperimentSession
from tmlib.models.dialect import compile_distributed_query
from tmlib.models.types import ST_SimplifyPreserveTopology
from tmlib.errors import RegexError
from tmlib.image import PyramidTile

logger = logging.getLogger(__name__)

#: Format string for channel layer locations
CHANNEL_LAYER_LOCATION_FORMAT = 'layer_{id}'


class ChannelLayer(ExperimentModel):

    '''A *channel layer* represents a multi-resolution overview of all images
    belonging to a given *channel*, *z-plane* and *time point*.
    as a pyramid in `Zoomify <http://www.zoomify.com/>`_ format.

    '''

    __tablename__ = 'channel_layers'

    __table_args__ = (UniqueConstraint('zplane', 'tpoint', 'channel_id'), )

    #: int: zero-based index in z stack
    zplane = Column(Integer, index=True)

    #: int: zero-based index in time series
    tpoint = Column(Integer, index=True)

    #: int: maximum intensity value at which images get clipped at original
    #: bit depth before rescaling to 8-bit
    max_intensity = Column(Integer)

    #: int: minimum intensity value at which images get clipped at original
    #: bit depth before rescaling to 8-bit
    min_intensity = Column(Integer)

    #: int: ID of parent channel
    channel_id = Column(
        Integer,
        ForeignKey('channels.id', onupdate='CASCADE', ondelete='CASCADE'),
        index=True
    )

    #: tmlib.models.channel.Channel: parent channel
    channel = relationship(
        'Channel',
        backref=backref('layers', cascade='all, delete-orphan')
    )

    def __init__(self, channel_id, tpoint, zplane):
        '''
        Parameters
        ----------
        channel_id: int
            ID of the parent channel
        tpoint: int
            zero-based time series index
        zplane: int
            zero-based z-resolution index
        '''
        self.tpoint = tpoint
        self.zplane = zplane
        self.channel_id = channel_id

    @cached_property
    def height(self):
        '''int: number of pixels along vertical axis at highest resolution level
        '''
        return self._maxzoom_image_size[0]

    @cached_property
    def width(self):
        '''int: number of pixels along horizontal axis at highest resolution
        level
        '''
        return self._maxzoom_image_size[1]

    @cached_property
    def depth(self):
        '''int: number of pixels along horizontal axis at highest resolution
        level
        '''
        return len(self.dimensions)

    @property
    def tile_size(self):
        '''int: maximal number of pixels along an axis of a tile'''
        return 256

    @property
    def zoom_factor(self):
        '''int: factor by which resolution increases per pyramid level'''
        return self.channel.experiment.zoom_factor

    @property
    def n_tiles(self):
        '''int: total number of tiles across all resolution levels'''
        return np.sum([np.prod(dims) for dims in self.dimensions])

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
            array of mappings with *y* and *x* coordinate as well as
            *y_offset* and *x_offset* relative to `image_file` for each tile
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
        for i, y in enumerate(row_info['indices']):
            y_offset = row_info['offsets'][i]
            is_overhanging_vertically = (
                (y_offset + self.tile_size) > site.image_size[0]
            )
            is_not_lower_plate_border = (y + 1) != self.dimensions[-1][0]
            is_not_lower_well_border = (site.y + 1) != well.dimensions[0]
            if is_overhanging_vertically and has_lower_neighbor:
                if (is_not_lower_plate_border and
                        is_not_lower_well_border):
                    continue
            for j, x in enumerate(col_info['indices']):
                x_offset = col_info['offsets'][j]
                is_overhanging_horizontally = (
                    (x_offset + self.tile_size) > site.image_size[1]
                )
                is_not_right_plate_border = (x + 1) != self.dimensions[-1][1]
                is_not_right_well_border = (site.x + 1) != well.dimensions[1]
                if is_overhanging_horizontally and has_right_neighbor:
                    if (is_not_right_plate_border and
                            is_not_right_well_border):
                        continue
                mappings.append({
                    'y': y,
                    'x': x,
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
        '''Maps tiles at the highest resolution level to all image files of
        the same channel, which intersect with the given tile. Only images
        bordering `site` to the left and/or top are considered.

        Parameters
        ----------
        site: tmlib.models.Site
            site whose neighbours could be included in the search

        Returns
        -------
        Dict[Tuple[int], List[int]]
            IDs of images intersecting with a given tile hashable by tile
            y, x coordinates
        '''
        experiment = self.channel.experiment
        session = Session.object_session(self)
        # Only consider sites to the left and/or top of the current site
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
            for y, x in itertools.product(row_indices, col_indices):
                mapping[(y, x)].append(fid)

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
            for y, x in itertools.product(row_indices, col_indices):
                mapping[(y, x)].append(fid)
        return mapping

    def calc_coordinates_of_next_higher_level(self, z, y, x):
        '''Calculates for a given tile the coordinates of the 4 tiles at the
        next higher zoom level that represent the tile at the current level.

        Parameters
        ----------
        z: int
            zero-based index of the current zoom level
        y: int
            zero-based index of the current row
        x: int
            zero-based index of the current column

        Returns
        -------
        List[Tuple[int]]
            row, column coordinate at the next higher zoom level
        '''
        coordinates = list()
        experiment = self.channel.experiment
        max_row, max_column = self.dimensions[z+1]
        rows = range(
            y * experiment.zoom_factor,
            (y * experiment.zoom_factor + experiment.zoom_factor - 1) + 1
        )
        cols = range(
            x * experiment.zoom_factor,
            (x * experiment.zoom_factor + experiment.zoom_factor - 1) + 1
        )
        for r, c in itertools.product(rows, cols):
            if r < max_row and c < max_column:
                coordinates.append((r, c))
        return coordinates

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

    @classmethod
    def delete_cascade(cls, connection):
        '''Deletes all instances for the given experiment as well as
        "children" instances of
        :class:`ChannelLayerTile <tmlib.models.tile.ChannelLayerTile>`.

        Parameters
        ----------
        experiment_id: int
            ID of the parent experiment

        Note
        ----
        This is not possible via the standard *SQLAlchemy* approach, because the
        table of :class:`ChannelLayerTile <tmlib.models.tile.ChannelLayerTile>`
        is distributed.
        '''
        logger.debug('delete channel layer tiles')
        connection.execute(
            compile_distributed_query('DELETE FROM channel_layer_tiles')
        )
        logger.debug('delete channel layers')
        connection.execute('DELETE FROM channel_layers;')

        def to_dict(self):
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
            % (self.__class__.__name__, self.id, self.channel_id,
                self.tpoint, self.zplane)
        )


class SegmentationLayer(ExperimentModel):

    __tablename__ = 'segmentation_layers'

    #: int: zero-based index in time series
    tpoint = Column(Integer, index=True)

    #: int: zero-based index in z stack
    zplane = Column(Integer, index=True)

    #: int: zoom level threshold below which polygons will not be visualized
    polygon_thresh = Column(Integer)

    #: int: zoom level threshold below which centroids will not be visualized
    centroid_thresh = Column(Integer)

    #: int: ID of parent channel
    mapobject_type_id = Column(
        Integer,
        ForeignKey('mapobject_types.id', onupdate='CASCADE', ondelete='CASCADE'),
        index=True
    )

    #: tmlib.models.mapobject.MapobjectType: parent mapobject type
    mapobject_type = relationship(
        'MapobjectType',
        backref=backref('layers', cascade='all, delete-orphan'),
    )

    def __init__(self, mapobject_type_id, tpoint=None, zplane=None):
        '''
        Parameters
        ----------
        mapobject_type_id: int
            ID of parent
            :class:`MapobjectType <tmlib.models.mapobject.MapobjectType>`
        tpoint: int, optional
            zero-based time point index
        zplane: int, optional
            zero-based z-resolution index
        '''
        self.tpoint = tpoint
        self.zplane = zplane
        self.mapobject_type_id = mapobject_type_id

    @classmethod
    def get_tile_bounding_box(cls, x, y, z, maxzoom):
        '''Calculates the bounding box of a layer tile.

        Parameters
        ----------
        x: int
            horizontal tile coordinate
        y: int
            vertical tile coordinate
        z: int
            zoom level
        maxzoom: int
            maximal zoom level of layers belonging to the visualized experiment

        Returns
        -------
        Tuple[int]
            bounding box coordinates (x_top, y_top, x_bottom, y_bottom)
        '''
        # The extent of a tile of the current zoom level in mapobject
        # coordinates (i.e. coordinates on the highest zoom level)
        size = 256 * 2 ** (maxzoom - z)
        # Coordinates of the top-left corner of the tile
        x0 = x * size
        y0 = y * size
        # Coordinates with which to specify all corners of the tile
        # NOTE: y-axis is inverted!
        minx = x0
        maxx = x0 + size
        miny = -y0
        maxy = -y0 - size
        return (minx, miny, maxx, maxy)

    def calculate_zoom_thresholds(self, maxzoom_level):
        '''Calculates the zoom level below which mapobjects are
        represented on the map as centroids rather than polygons and the
        zoom level below which mapobjects are no longer visualized at all.
        These thresholds are necessary, because it would result in too much
        network traffic and the client would be overwhelmed by the large number
        of objects.

        Parameters
        ----------
        maxzoom_level: int
            maximum zoom level of the pyramid

        Returns
        -------
        Tuple[int]
            threshold zoom levels for visualization of polygons and centroids

        Note
        ----
        The optimal threshold levels depend on the number of points on the
        contour of objects, but also the size of the browser window and the
        resolution settings of the browser.
        '''
        # TODO: This is too simplistic. Calculate optimal zoom level by
        # sampling mapobjects at the highest resolution level and approximate
        # number of points that would be sent to the client.
        if self.mapobject_type.ref_type is None:
            polygon_thresh = 0
            centroid_thresh = 0
        else:
            polygon_thresh = maxzoom_level - 4
            polygon_thresh = 0 if polygon_thresh < 0 else polygon_thresh
            centroid_thresh = polygon_thresh - 2
            centroid_thresh = 0 if centroid_thresh < 0 else centroid_thresh
        return (polygon_thresh, centroid_thresh)

    def get_segmentations(self, x, y, z, tolerance=2):
        '''Get outlines of each
        :class:`Mapobject <tmlib.models.mapobject.Mapobject>`
        contained by a given pyramid tile.

        Parameters
        ----------
        x: int
            zero-based column map coordinate at the given `z` level
        y: int
            zero-based row map coordinate at the given `z` level
            (negative integer values due to inverted *y*-axis)
        z: int
            zero-based zoom level index
        tolerance: int, optional
            maximum distance in pixels between points on the contour of
            original polygons and simplified polygons;
            the higher the `tolerance` the less coordinates will be used to
            describe the polygon and the less accurate it will be
            approximated and; if ``0`` the original polygon is used
            (default: ``2``)

        Returns
        -------
        List[Tuple[int, str]]
            GeoJSON representation of each selected mapobject

        Note
        ----
        If *z* > `polygon_thresh` mapobjects are represented by polygons, if
        `polygon_thresh` < *z* < `centroid_thresh`,
        mapobjects are represented by points and if *z* < `centroid_thresh`
        they are not represented at all.
        '''
        logger.debug('get mapobject outlines falling into tile')
        session = Session.object_session(self)

        maxzoom = self.mapobject_type.experiment.pyramid_depth - 1
        do_simplify = self.centroid_thresh <= z < self.polygon_thresh
        do_nothing = z < self.centroid_thresh
        if do_nothing:
            logger.debug('dont\'t represent objects')
            return list()
        elif do_simplify:
            logger.debug('represent objects by centroids')
            query = session.query(
                MapobjectSegmentation.mapobject_id,
                MapobjectSegmentation.geom_centroid.ST_AsGeoJSON()
            )
        else:
            logger.debug('represent objects by polygons')
            tolerance = (maxzoom - z) ** 2 + 1
            logger.debug('simplify polygons using tolerance %d', tolerance)
            query = session.query(
                MapobjectSegmentation.mapobject_id,
                MapobjectSegmentation.geom_polygon.
                ST_SimplifyPreserveTopology(tolerance).ST_AsGeoJSON()
            )

        minx, miny, maxx, maxy = self.get_tile_bounding_box(x, y, z, maxzoom)
        tile = (
            'POLYGON(('
                '{maxx} {maxy}, {minx} {maxy}, {minx} {miny}, {maxx} {miny}, '
                '{maxx} {maxy}'
            '))'.format(minx=minx, maxx=maxx, miny=miny, maxy=maxy)
        )

        outlines = query.filter(
            MapobjectSegmentation.segmentation_layer_id == self.id,
            MapobjectSegmentation.geom_polygon.ST_Intersects(tile)
        ).\
        all()

        if len(outlines) == 0:
            logger.warn(
                'no outlines found for objects of type "%s" within tile: '
                'x=%d, y=%d, z=%d', self.mapobject_type.name, x, y, z
            )

        return outlines

    def __repr__(self):
        return (
            '<%s(id=%d, mapobject_type_id=%r)>'
            % (self.__class__.__name__, self.id, self.mapobject_type_id)
        )

