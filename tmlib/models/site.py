import logging
import numpy as np
from sqlalchemy import Column, Integer, ForeignKey, Boolean
from sqlalchemy.orm import relationship, backref
from sqlalchemy import UniqueConstraint

from tmlib.models.base import ExperimentModel, DateMixIn


logger = logging.getLogger(__name__)


class Site(ExperimentModel, DateMixIn):

    '''A *site* is a unique `y`, `x` position projected onto the
    *plate* bottom plane that was scanned by the microscope.

    Attributes
    ----------
    shifts: [tmlib.models.SiteShifts]
        shifts belonging to the site
    intersection: tmlib.models.SiteIntersection
        intersection belongings to the site
    channel_image_files: List[tmlib.models.ChannelImageFile]
        channel image files belonging to the site
    mapobject_segmentations: List[tmlib.models.MapobjectSegmentation]
        segmentations belonging to the site
    '''

    __tablename__ = 'sites'

    __table_args__ = (UniqueConstraint('x', 'y', 'well_id'), )

    #: int: zero-based row index of the image within the well
    y = Column(Integer, index=True)

    #: int: zero-based column index of the image within the well
    x = Column(Integer, index=True)

    #: int: number of pixels along the vertical axis of the image
    height = Column(Integer, index=True)

    #: int: number of pixels along the horizontal axis of the image
    width = Column(Integer, index=True)

    #: bool: whether the site should be omitted from further analysis
    omitted = Column(Boolean, index=True)

    #: int: ID of parent well
    well_id = Column(
        Integer,
        ForeignKey('wells.id', onupdate='CASCADE', ondelete='CASCADE'),
        index=True
    )

    #: tmlib.models.well.Well: parent well
    well = relationship(
        'Well',
        backref=backref('sites', cascade='all, delete-orphan')
    )

    def __init__(self, y, x, height, width, well_id, omitted=False):
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
        omitted: bool, optional
            whether the image file is considered empty, i.e. consisting only of
            background pixels without having biologically relevant information
            (default: ``False``)
        '''
        self.y = y
        self.x = x
        self.height = height
        self.width = width
        self.well_id = well_id
        self.omitted = omitted

    @property
    def coordinate(self):
        '''Tuple[int]: row, column coordinate of the site within the well'''
        return (self.y, self.x)

    @property
    def image_size(self):
        '''Tuple[int]: number of pixels along the vertical (*y*) and horizontal
        (*x*) axis, i.e. height and width of the site
        '''
        return (self.height, self.width)

    @property
    def offset(self):
        '''Tuple[int]: *y*, *x* coordinate of the top, left corner of the site
        relative to the layer overview at the maximum zoom level
        '''
        logger.debug('calculate offset for site %d', self.id)
        well = self.well
        plate = well.plate
        experiment = plate.experiment
        y_offset = (
            # Sites in the well above the site
            self.y * self.image_size[0] +
            # Potential displacement of sites in y-direction
            self.y * experiment.vertical_site_displacement +
            # Wells and plates above the well
            well.offset[0]
        )
        x_offset = (
            # Sites in the well left of the site
            self.x * self.image_size[1] +
            # Potential displacement of sites in y-direction
            self.x * experiment.horizontal_site_displacement +
            # Wells and plates left of the well
            well.offset[1]
        )
        return (y_offset, x_offset)

    def __repr__(self):
        return (
            '<Site(id=%r, well_id=%r, y=%r, x=%r)>'
            % (self.id, self.well_id, self.y, self.x)
        )
