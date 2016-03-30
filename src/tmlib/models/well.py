import re
import numpy as np
import logging
from cached_property import cached_property
from sqlalchemy import Column, String, Integer, ForeignKey
from sqlalchemy.orm import relationship

from .. import utils
from tmlib.models import Model, DateMixIn

logger = logging.getLogger(__name__)


class Well(Model, DateMixIn):

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

    #: str: name of the corresponding database table
    __tablename__ = 'wells'

    # Table columns
    name = Column(String, index=True)
    plate_id = Column(Integer, ForeignKey('plates.id'))

    # Relationships to other tables
    plate = relationship('Plate', backref='wells')

    def __init__(self, name, plate_id):
        '''
        Parameters
        ----------
        name: str
            name of the well
        plate_id: int
            ID of the parent plate
        '''
        # TODO: ensure that name is unique within plate
        self.name = name
        self.plate_id = plate_id

    @property
    def coordinate(self):
        '''Tuple[int]: row, column coordinate of the well within the plate'''
        return self.map_name_to_coordinate(self.name)

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
    def image_size(self):
        '''Tuple[int]: number of pixels along the vertical and horizontal axis
        '''
        vertical_offset = self.plate.experiment.vertical_site_displacement
        horizontal_offset = self.plate.experiment.horizontal_site_displacement
        rows, cols = self.dimensions
        site_dims = self.sites[0].image_size
        return (
            rows * site_dims[0] + vertical_offset * (rows - 1),
            cols * site_dims[1] + horizontal_offset * (cols - 1)
        )

    @staticmethod
    def map_name_to_coordinate(name):
        '''Map the identifier string representation to the coordinate, i.e.
        zero-based index position.

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
        >>>Well.map_name_to_coordinate("A02")
        (0, 1)
        '''
        row_name, col_name = re.match(r'([A-Z])(\d{2})', name).group(1, 2)
        row_index = utils.map_letter_to_number(row_name) - 1
        col_index = int(col_name) - 1
        return (row_index, col_index)

    @staticmethod
    def map_coordinate_to_name(coordinate):
        '''Map the zero-based index position to the identifier string
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
        >>>Well.map_coordinate_to_name((0, 1))
        "A02"
        '''
        row_index, col_index = coordinate[0], coordinate[1]
        row_name = utils.map_number_to_letter(row_index + 1)
        return '%s%.2d' % (row_name, col_index + 1)

    def __repr__(self):
        return '<Well(id=%r, name=%r)>' % (self.id, self.name)
