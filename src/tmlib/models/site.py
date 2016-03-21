import logging
from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship

from tmlib.models import Model

logger = logging.getLogger(__name__)


class Site(Model):

    '''
    A *site* is a unique y,x position projected onto the plane of the *plate*
    bottom, which was scanned by the microscope.
    '''

    #: Name of the corresponding database table
    __tablename__ = 'sites'

    #: Table columns
    well_position_y = Column(Integer, index=True)
    well_position_x = Column(Integer, index=True)
    y_shift = Column(Integer)
    x_shift = Column(Integer)
    upper_overhang = Column(Integer)
    lower_overhang = Column(Integer)
    right_overhang = Column(Integer)
    left_overhang = Column(Integer)
    well_id = Column(Integer, ForeignKey('wells.id'))

    #: Relationships to other tables
    well = relationship('Well', backref='sites')

    def __init__(self, well_position_y, well_position_x, well):
        '''
        Parameters
        ----------
        well_position_y: int
            zero-based row index of the image within the well
        well_position_x: int
            zero-based column index of the image within the well
        well: tmlib.well.Well
            parent well to which the site belongs
        '''
        self.well_position_y = well_position_y
        self.well_position_x = well_position_x
        self.well = well
        self.well_id = well.id

    @property
    def well_coordinate(self):
        '''
        Returns
        -------
        Tuple[int]
            row, column coordinate of the site within the well
        '''
        return (self.well_position_y, self.well_position_x)

    def __repr__(self):
        return (
            '<Site(id=%r, well_name=%r, well_position_y=%r, well_position_x=%r)>'
            % (self.id, self.well.name, self.well_position_y, self.well_position_x)
        )
    
