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
    alignment: tmlib.well.SiteAlignments
        alignment that belongs to the site
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


class SiteAlignment(Model):

    '''A *site* may be shifted between different *cycles* and needs to be
    aligned between them.

    Attributes
    ----------
    x_shift: int
        shift in pixels along the x-axis relative to the corresponding
        site of the reference cycle
        (positive value -> right, negative value -> left)
    y_shift: int
        shift in pixels along the y-axis relative to the corresponding
        site of the reference cycle
        (positive value -> down, negative value -> up)
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
    cycle_id: int
        ID of the parent cycle
    cycle: tmlib.models.Cycle
        parent cycle to which the site belongs
    '''

    #: Name of the corresponding database table
    __tablename__ = 'site_alignments'

    # Table columns
    y_shift = Column(Integer)
    x_shift = Column(Integer)
    upper_overhang = Column(Integer)
    lower_overhang = Column(Integer)
    right_overhang = Column(Integer)
    left_overhang = Column(Integer)
    site_id = Column(Integer, ForeignKey('sites.id'))
    cycle_id = Column(Integer, ForeignKey('cycles.id'))

    # Relationships to other tables
    site = relationship('Site', backref='alignment')  # one-to-one
    cycle = relationship('Cycle', backref='site_alignments')

    def __init__(self, x_shift, y_shift, upper_overhang, lower_overhang,
                 right_overhang, left_overhang, site_id, cycle_id):
        '''
        Parameters
        ----------
        x_shift: int
            shift in pixels along the x-axis relative to the corresponding
            site of the reference cycle
            (positive value -> right, negative value -> left)
        y_shift: int
            shift in pixels along the y-axis relative to the corresponding
            site of the reference cycle
            (positive value -> down, negative value -> up)
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
        cycle_id: int
            ID of the parent cycle
        '''
        self.x_shift = x_shift
        self.y_shift = y_shift
        self.upper_overhang = upper_overhang
        self.lower_overhang = lower_overhang
        self.right_overhang = right_overhang
        self.left_overhang = left_overhang
        self.site_id = site_id
        self.cycle_id = cycle_id
