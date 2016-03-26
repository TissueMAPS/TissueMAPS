import logging
from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship

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

    #: Name of the corresponding database table
    __tablename__ = 'sites'

    # Table columns
    y = Column(Integer, index=True)
    x = Column(Integer, index=True)
    well_id = Column(Integer, ForeignKey('wells.id'))

    # Relationships to other tables
    well = relationship('Well', backref='sites')

    def __init__(self, y, x, well_id):
        '''
        Parameters
        ----------
        y: int
            zero-based row index of the image within the well
        x: int
            zero-based column index of the image within the well
        well_id: int
            ID of the parent well
        '''
        self.y = y
        self.x = x
        self.well_id = well_id

    @property
    def well_coordinate(self):
        '''Tuple[int]: row, column coordinate of the site within the well'''
        return (self.y, self.x)

    def __repr__(self):
        return (
            '<Site(id=%r, well=%r, y=%r, x=%r)>'
            % (self.id, self.well.name, self.y, self.x)
        )


class SiteShift(Model):

    '''A *site* may be shifted between different *cycles* and needs to be
    aligned between them.

    Attributes
    ----------
    x: int
        shift in pixels along the x-axis relative to the corresponding
        site of the reference cycle
        (positive value -> right, negative value -> left)
    y: int
        shift in pixels along the y-axis relative to the corresponding
        site of the reference cycle
        (positive value -> down, negative value -> up)
    site_id: int
        ID of the parent site
    site: tmlib.models.Site
        parent site to which the site belongs
    cycle_id: int
        ID of the parent cycle
    cycle: tmlib.models.Cycle
        parent cycle to which the site belongs
    '''

    #: Name of the corresponding database table
    __tablename__ = 'site_shifts'

    # Table columns
    y = Column(Integer)
    x = Column(Integer)
    site_id = Column(Integer, ForeignKey('sites.id'))
    cycle_id = Column(Integer, ForeignKey('cycles.id'))

    # Relationships to other tables
    site = relationship('Site', backref='shifts')
    cycle = relationship('Cycle', backref='site_shifts')

    def __init__(self, x, y, site_id, cycle_id):
        '''
        Parameters
        ----------
        x: int
            shift in pixels along the x-axis relative to the corresponding
            site of the reference cycle
            (positive value -> right, negative value -> left)
        y: int
            shift in pixels along the y-axis relative to the corresponding
            site of the reference cycle
            (positive value -> down, negative value -> up)
        site_id: int
            ID of the parent site
        cycle_id: int
            ID of the parent cycle
        '''
        self.x = x
        self.y = y
        self.site_id = site_id
        self.cycle_id = cycle_id

    def __repr__(self):
        return (
            '<SiteShift(id=%r, y=%r, x=%r)>'
            % (self.id, self.y, self.x)
        )


class SiteIntersection(Model):

    '''When *sites* are shifted between *cycles*, they only have a subset
    of pixels in common. In order to be able to overlay images of
    different *cycles*, images need to be cropped such that the intersecting
    pixels are aligned.

    Attributes
    ----------
    upper_overhang: int
        overhanging pixels at the top
    lower_overhang: int
        overhanging pixels at the bottom
    right_overhang: int
        overhanging pixels at the right side
    left_overhang: int
        overhanging pixels at the left side
    site_id: int
        ID of the parent site
    site: tmlib.models.Site
        parent site to which the site belongs
    '''

    #: Name of the corresponding database table
    __tablename__ = 'site_intersections'

    # Table columns
    upper_overhang = Column(Integer)
    lower_overhang = Column(Integer)
    right_overhang = Column(Integer)
    left_overhang = Column(Integer)
    site_id = Column(Integer, ForeignKey('sites.id'))

    # Relationships to other tables
    site = relationship('Site', backref='intersection', uselist=False)

    def __init__(self, upper_overhang, lower_overhang,
                 right_overhang, left_overhang, site_id):
        '''
        Parameters
        ----------
        upper_overhang: int
            overhanging pixels at the top
        lower_overhang: int
            overhanging pixels at the bottom
        right_overhang: int
            overhanging pixels at the right side
        left_overhang: int
            overhanging pixels at the left side
        site_id: int
            ID of the parent site
        '''
        self.upper_overhang = upper_overhang
        self.lower_overhang = lower_overhang
        self.right_overhang = right_overhang
        self.left_overhang = left_overhang
        self.site_id = site_id
