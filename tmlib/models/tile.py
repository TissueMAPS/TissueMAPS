import os
import logging
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

    Attributes
    ----------
    level: int
        zero-based zoom level index
    row: int
        zero-based row index of the tile at given `level`
    column: int
        zero-based column index of the tile at given zoom `level`
    channel_layer_id: int
        ID of the parent channel pyramid
    channel_pyramid: tmlib.models.ChannelLayer
        parent channel pyramid to which the tile belongs
    pixels: tmlib.image.PyramidTile
        binary image data encoded as JPEG
    '''

    __tablename__ = 'channel_layer_tiles'

    __table_args__ = (
        UniqueConstraint(
            'level', 'row', 'column', 'channel_layer_id'
        ),
        Index(
            'ix_channel_layer_tiles_level_row_column_channel_layer_id',
            'level', 'row', 'column', 'channel_layer_id'
        )
    )

    __distribute_by_hash__ = 'id'

    _pixels = Column('pixels', BYTEA)

    #: int: zero-based zoom level (z) index
    level = Column(Integer)

    #: int: zero-baesed vertical (y) index
    row = Column(Integer)

    #: int: zero-baesed horizontal (x) index
    column = Column(Integer)

    #ALTER TABLE channel_layer_tiles ALTER COLUMN pixels SET STORAGE MAIN;

    #: int: ID of parent channel layer
    channel_layer_id = Column(
        Integer,
        ForeignKey('channel_layers.id', onupdate='CASCADE', ondelete='CASCADE'),
        index=True
    )

    #: tmlib.models.layer.ChannelLayer: parent channel layer
    channel_layer = relationship(
        'ChannelLayer',
        backref=backref('pyramid_tile_files', cascade='all, delete-orphan')
    )

    def __init__(self, level, row, column, channel_layer_id, pixels=None):
        '''
        Parameters
        ----------
        level: int
            zero-based zoom level index
        row: int
            zero-based row index of the tile at given `level`
        column: int
            zero-based column index of the tile at given zoom `level`
        channel_layer_id: int
            ID of the parent channel pyramid
        pixels: tmlib.image.PyramidTile, optional
            pixels array (default: ``None``)
        '''
        self.row = row
        self.column = column
        self.level = level
        self.channel_layer_id = channel_layer_id
        self.pixels = pixels

    @hybrid_property
    def pixels(self):
        '''tmlib.image.PyramidTile: JPEG encoded tile'''
        # TODO: consider creating a custom SQLAlchemy column type
        metadata = PyramidTileMetadata(
            level=self.level, row=self.row, column=self.column,
            channel_layer_id=self.channel_layer.id
        )
        return PyramidTile.create_from_binary(self._pixels, metadata)

    @pixels.setter
    def pixels(self, tile):
        # TODO: It might be better to use Postgis raster format, but there don't
        # seem to be good solutions for inserting raster data via SQLAlchemy
        if tile is not None:
            self._pixels = tile.jpeg_encode()
        else:
            self._pixels = None

    def __repr__(self):
        return '<%s(id=%r, row=%r, column=%r, level=%r)>' % (
            self.__class__.__name__, self.id, self.row, self.column, self.level
        )


