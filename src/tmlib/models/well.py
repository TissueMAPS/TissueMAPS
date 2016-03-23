import re
import numpy as np
import logging
from cached_property import cached_property
from sqlalchemy import Column, String, Integer, ForeignKey
from sqlalchemy.orm import relationship

from .. import utils
from tmlib.models import Model, DateMixIn

logger = logging.getLogger(__name__)


class Well(DateMixIn, Model):

    '''A *well* is a reservoir for biological samples and multiple *wells* are
    typically arranged as a grid on a *plate*.
    From an imaging point of view, a *well* represents a continuous area of
    image acquisition projected onto the y,x plane of the *plate* bottom.
    Images may not be acquired continuously along the z axis, however,
    and a full volume reconstruction therefore not possible.

    Attributes
    ----------
    name: str
        name of the well
    plate_id: int
        ID of the parent plate
    plate: tmlib.models.Plate
        parent plate to which the well belongs
    '''

    #: Name of the corresponding database table
    __tablename__ = 'wells'

    # Table columns
    name = Column(String, index=True)
    plate_id = Column(Integer, ForeignKey('plates.id'))

    # Relationships to other tables
    plate = relationship('Plate', backref='wells')

    def __init__(self, name, plate):
        '''
        Parameters
        ----------
        name: str
            name of the well
        plate: tmlib.models.Plate
            parent plate to which the well belongs
        '''
        # TODO: ensure that name is unique within plate
        self.name = name
        self.plate_id = plate.id

    @property
    def plate_coordinate(self):
        '''Tuple[int]: row, column coordinate of the well within the plate'''
        return self.map_name_to_plate_coordinate(self.name)

    @cached_property
    def dimensions(self):
        '''Tuple[int]: number of sites in the well along the vertical and
        horizontal axis, i.e. the number of rows and columns
        '''
        return tuple(np.sum(
            np.array(
                [(s.well_position_y, s.well_position_x) for s in self.sites]
            ),
            axis=0
        ))

    @staticmethod
    def map_name_to_plate_coordinate(name):
        '''
        Mapping of the identifier string representation to the
        one-based index position, e.g. "A02" -> (1, 2)

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
        >>>Well.map_name_to_plate_coordinate("A02")
        (0, 1)
        '''
        row_name, col_name = re.match(r'([A-Z])(\d{2})', name).group(1, 2)
        row_index = utils.map_letter_to_number(row_name) - 1
        col_index = int(col_name) - 1
        return (row_index, col_index)

    @staticmethod
    def map_plate_coordinate_to_name(coordinate):
        '''
        Mapping of the one-based index position to the identifier string
        representation.

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
        >>>Well.map_plate_coordinate_to_name((0, 1))
        "A02"
        '''
        row_index, col_index = coordinate[0], coordinate[1]
        row_name = utils.map_number_to_letter(row_index + 1)
        return '%s%.2d' % (row_name, col_index + 1)

    def __repr__(self):
        return '<Well(id=%r, name=%r)>' % (self.id, self.name)
