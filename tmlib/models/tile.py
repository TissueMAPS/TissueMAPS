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
import logging
import psycopg2
import numpy as np
from sqlalchemy import Column, String, Integer, Boolean, ForeignKey, Index
from sqlalchemy.dialects.postgresql import BYTEA
from sqlalchemy.orm import relationship, backref
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy import UniqueConstraint

from tmlib.image import PyramidTile
from tmlib.metadata import PyramidTileMetadata
from tmlib.models import ExperimentModel

logger = logging.getLogger(__name__)


class ChannelLayerTile(ExperimentModel):

    '''A *channel layer tile* is a component of an image pyramid. Each tile
    holds a single 2D 8-bit pixel plane with pre-defined dimensions.

    '''

    __tablename__ = 'channel_layer_tiles'

    __table_args__ = (
        UniqueConstraint(
            'channel_layer_id', 'z', 'y', 'x'
        ),
        Index(
            'ix_channel_layer_tiles_channel_layer_id_z_y_x',
            'channel_layer_id', 'z', 'y', 'x'
        )
    )

    # NOTE: Distributing by "id" would be ideal, but it leads to
    # issues upon upserting: the distribution key needs to be part of
    # UNIQUE and PRIMARY KEY constraints and the value for "id" cannot be
    # auto-generated using SEQUENCE. Distribution by "channel_layer_id"
    # would balance data unequally over available shards, because
    # there are typically only a few layers. In this case, rows would
    # accumulate in a small number of large shards
    # which has a negative impact on query performance.
    __distribute_by_hash__ = 'y'

    _pixels = Column('pixels', BYTEA)

    #: int: zero-based zoom level index
    z = Column(Integer, nullable=False)

    #: int: zero-based coordinate on vertical axis
    y = Column(Integer, nullable=False)

    #: int: zero-based coordinate on horizontal axis
    x = Column(Integer, nullable=False)

    # TODO: Add polygon geometry for bounding box of pixels to simplify
    # geometric queries. This allow selecting pyramid tiles that contain
    # certain mapobjects, for example. Ultimately, this could be implemented
    # as Postgis raster, but there is no good Python interface for conversion
    # between rasters and numpy arrays.

    #: int: ID of parent channel layer
    channel_layer_id = Column(Integer, nullable=False)

    def __init__(self, z, y, x, channel_layer_id, pixels=None):
        '''
        Parameters
        ----------
        z: int
            zero-based zoom level index
        y: int
            zero-based row index of the tile at given zoom level
        x: int
            zero-based column index of the tile at given zoom level
        channel_layer_id: int
            ID of the parent channel pyramid
        pixels: tmlib.image.PyramidTile, optional
            pixels array (default: ``None``)
        '''
        self.y = y
        self.x = x
        self.z = z
        self.channel_layer_id = channel_layer_id
        self.pixels = pixels

    @hybrid_property
    def pixels(self):
        '''tmlib.image.PyramidTile: pixel array'''
        # TODO: consider creating a custom SQLAlchemy column type
        metadata = PyramidTileMetadata(
            z=self.z, y=self.y, x=self.x,
            channel_layer_id=self.channel_layer_id
        )
        return PyramidTile.create_from_binary(self._pixels, metadata)

    @pixels.setter
    def pixels(self, tile):
        # TODO: It might be better to use Postgis raster format, but there don't
        # seem to be good solutions for inserting raster data via Python
        # using numpy arrays.
        if tile is not None:
            self._pixels = tile.jpeg_encode()
        else:
            self._pixels = None

    @classmethod
    def add(cls, connection, channel_layer_id, z, y, x, tile):
        '''Adds a new record.

        Parameters
        ----------
        connection: psycopg2.extras.NamedTupleCursor
            experiment-specific database connection created via
        channel_layer_id: int
            ID of the parent
            :class:`ChannelLayer <tmlib.models.layer.ChannelLayer>`
        z: int
            zero-based *z*-coordinate
        y: int
            zero-based *y*-coordinate
        x: int
            zero-based *x*-coordinate
        tile: tmlib.image.PyramidTile
            tile encoding pixel values

        Return
        ------
        int
            ID of the added record
        '''
        # Upsert the tile entry, i.e. insert or update if exists
        # NOTE: The UPSERT has some overhead and it may be more performant to
        # DELETE tiles first and then INSERT new ones without UPDATE.
        connection.execute('''
            INSERT INTO channel_layer_tiles AS t (
                channel_layer_id, z, y, x, pixels
            )
            VALUES (
                %(channel_layer_id)s, %(z)s, %(y)s, %(x)s, %(pixels)s
            )
            ON CONFLICT
            ON CONSTRAINT channel_layer_tiles_channel_layer_id_z_y_x_key
            DO UPDATE
            SET pixels = %(pixels)s
            WHERE t.channel_layer_id = %(channel_layer_id)s
            AND t.z = %(z)s AND t.y = %(y)s AND t.x = %(x)s;
        ''', {
            'channel_layer_id': channel_layer_id, 'z': z, 'y': y, 'x': x,
            'pixels': psycopg2.Binary(tile.jpeg_encode().tostring())
        })

    def __repr__(self):
        return '<%s(z=%r, y=%r, x=%r, channel_layer_id=%r)>' % (
            self.__class__.__name__, self.z, self.y, self.x,
            self.channel_layer_id
        )


