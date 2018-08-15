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
import re
import numpy as np
import logging
from cached_property import cached_property
from sqlalchemy import (
    Column, String, Integer, ForeignKey, Index, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship, backref

from tmlib import utils
from tmlib.models.base import ExperimentModel, DateMixIn, IdMixIn


logger = logging.getLogger(__name__)


class Well(ExperimentModel, DateMixIn, IdMixIn):

    '''A *well* is a reservoir for a biological sample and multiple *wells* are
    typically arranged as a grid on a :class:`Plate <tmlib.models.plate.Plate>`.

    Note
    ----
    From an imaging point of view, a *well* is assumed to be a continuous area
    of image acquisition when projected onto an *y*/*x* plane. Even if images
    were not acquired in a continous way, they will be stitched together.

    '''

    __tablename__ = 'wells'

    __table_args__ = (
        UniqueConstraint('name', 'plate_id'),
        Index('ix_wells_description', 'description', postgres_using='gin')
    )

    #: str: name assinged by the application, e.g. ``"A01"``
    name = Column(String, index=True)

    #: dict: description of the well content in form of a mapping to store
    #: for example the name or ID of a stain, compound or gene
    description = Column(JSONB)

    #: int: ID of parent plate
    plate_id = Column(
        Integer,
        ForeignKey('plates.id', onupdate='CASCADE', ondelete='CASCADE'),
        index=True
    )

    #: tmlib.models.plate.Plate: parent plate
    plate = relationship(
        'Plate',
        backref=backref('wells', cascade='all, delete-orphan')
    )

    def __init__(self, name, plate_id, description=None):
        '''
        Parameters
        ----------
        name: str
            name of the well
        plate_id: int
            ID of the parent plate
        description: Dict[str, Union[str, int, float, bool, List, Dict]], optional
            description of the well content
        '''
        if not name.isalnum():
            raise ValueError('Well name must be alphanumeric.')
        if not len(name) == 3:
            raise ValueError('Well name must have 3 characters.')
        if not name[0].isalpha():
            raise ValueError('First character of well name must be alphabetic.')
        if not name[0].isupper():
            raise ValueError('First character of well name must be upper case.')
        if not name[1:].isdigit():
            raise ValueError(
                'Second and thrid character of well name must be numeric.'
            )
        self.name = name
        self.plate_id = plate_id
        self.description = (description if description is not None else {})

    @property
    def coordinate(self):
        '''Tuple[int]: row, column coordinate of the well within the plate'''
        return self.map_name_to_coordinate(self.name)

    @property
    def x(self):
        '''int: zero-based *x*-coordinate (column) of the well within the plate
        '''
        return self.coordinate[1]

    @property
    def y(self):
        '''int: zero-based *y*-coordinate (row) of the well within the plate'''
        return self.coordinate[0]

    @cached_property
    def site_grid(self):
        '''numpy.ndarray[int]: IDs of sites arranged according to their
        relative position within the well
        '''
        cooridinates = [s.cooridinate for s in self.sites]
        height, width = self.dimensions
        grid = np.zeros((height, width), dtype=int)
        for i, c in enumerate(cooridinates):
            grid[c[0], c[1]] = self.sites[i].id
        return grid

    @cached_property
    def dimensions(self):
        '''Tuple[int]: number of sites in the well along the vertical and
        horizontal axis, i.e. the number of rows and columns
        '''
        return tuple(
            np.amax(np.array([(s.y, s.x) for s in self.sites]), axis=0) + 1
        )

    @cached_property
    def _image_size(self):
        vertical_offset = self.plate.experiment.vertical_site_displacement
        horizontal_offset = self.plate.experiment.horizontal_site_displacement
        rows, cols = self.dimensions
        site_dims = self.sites[0].image_size
        return (
            rows * site_dims[0] + vertical_offset * (rows - 1),
            cols * site_dims[1] + horizontal_offset * (cols - 1)
        )

    @cached_property
    def image_size(self):
        '''Tuple[int]: number of pixels along the vertical and horizontal axis
        '''
        return self.plate._well_image_size

    @staticmethod
    def map_name_to_coordinate(name):
        '''Maps identifier string representation to coordinate.

        Parameters
        ----------
        name: str
            well name

        Returns
        -------
        Tuple[int]
            zero-based row, column position of a given well within the plate

        Examples
        --------
        >>> Well.map_name_to_coordinate("A02")
        (0, 1)
        '''
        row_name, col_name = re.match(r'([A-Z])(\d+)', name).group(1, 2)
        row_index = utils.map_letter_to_number(row_name) - 1
        col_index = int(col_name) - 1
        return (row_index, col_index)

    @staticmethod
    def map_coordinate_to_name(coordinate):
        '''Maps coordinate to identifier string representation.

        Parameters
        ----------
        coordinate: Tuple[int]
            zero-based row, column position of a given well within the plate

        Returns
        -------
        str
            identifier string representation of a well

        Examples
        --------
        >>> Well.map_coordinate_to_name((0, 1))
        "A02"
        '''
        row_index, col_index = coordinate[0], coordinate[1]
        row_name = utils.map_number_to_letter(row_index + 1)
        return '%s%.2d' % (row_name, col_index + 1)

    @cached_property
    def offset(self):
        '''Tuple[int]: *y*, *x* coordinate of the top, left corner of the site
        relative to the layer overview at the maximum zoom level
        '''
        logger.debug('calculate offset of well %d', self.id)
        plate = self.plate
        n_rows = plate.nonempty_rows.index(self.y)
        n_columns = plate.nonempty_columns.index(self.x)
        experiment = plate.experiment
        # NOTE: Since wells are allowed to have different sizes,
        # we cannot use the size of individual wells to caluculate the offset,
        # but rather have to use the same size for all wells
        # (determined at the plate level)
        y_offset = (
            # Wells in the plate above the well
            n_rows * self.image_size[0] +
            # Gaps introduced between wells
            n_rows * experiment.well_spacer_size +
            # Plates above the plate
            plate.offset[0]
        )
        x_offset = (
            # Wells in the plate left of the well
            n_columns * self.image_size[1] +
            # Gaps introduced between wells
            n_columns * experiment.well_spacer_size +
            # Plates left of the plate
            plate.offset[1]
        )
        return (y_offset, x_offset)

    def __repr__(self):
        return '<Well(id=%r, name=%r)>' % (self.id, self.name)
