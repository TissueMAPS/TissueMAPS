import logging
from cached_property import cached_property
from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy import UniqueConstraint

from tmlib.models import Model, DateMixIn

logger = logging.getLogger(__name__)


class Site(Model, DateMixIn):

    '''A *site* is a unique `y`, `x` position projected onto the
    *plate* bottom plane that was scanned by the microscope.

    Attributes
    ----------
    y: int
        zero-based row index of the image within the well
    x: int
        zero-based column index of the image within the well
    height: int
        number of pixels along the vertical axis of the site
    width: int
        number of pixels along the horizontal axis of the site
    well_id: int
        ID of the parent well
    well: tmlib.well.Well
        parent well to which the site belongs
    shifts: [tmlib.models.SiteShifts]
        shifts that belong to the site
    intersection: tmlib.models.SiteIntersection
        intersection that belongs to the site
    channel_image_files: List[tmlib.models.ChannelImageFile]
        channel image files that belong to the site
    '''

    #: str: name of the corresponding database table
    __tablename__ = 'sites'

    __table_args__ = (UniqueConstraint('x', 'y', 'well_id'), )

    # Table columns
    y = Column(Integer, index=True)
    x = Column(Integer, index=True)
    height = Column(Integer, index=True)
    width = Column(Integer, index=True)
    well_id = Column(Integer, ForeignKey('wells.id'))

    # Relationships to other tables
    well = relationship('Well', backref='sites')

    def __init__(self, y, x, height, width, well_id):
        '''
        Parameters
        ----------
        y: int
            zero-based row index of the image within the well
        x: int
            zero-based column index of the image within the well
        height: int
            number of pixels along the vertical axis of the site
        width: int
            number of pixels along the horizontal axis of the site
        well_id: int
            ID of the parent well
        '''
        self.y = y
        self.x = x
        self.height = height
        self.width = width
        self.well_id = well_id

    @property
    def coordinate(self):
        '''Tuple[int]: row, column coordinate of the site within the well'''
        return (self.y, self.x)

    @cached_property
    def image_size(self):
        '''Tuple[int]: number of pixels along the vertical (*y*) and horizontal
        (*x*) axis, i.e. height and width of the site
        '''
        return (self.height, self.width)

    def __repr__(self):
        return (
            '<Site(id=%r, well=%r, y=%r, x=%r)>'
            % (self.id, self.well.name, self.y, self.x)
        )
