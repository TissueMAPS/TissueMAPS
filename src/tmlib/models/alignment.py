import logging
from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship, backref

from tmlib.models import Model

logger = logging.getLogger(__name__)


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

    #: str: name of the corresponding database table
    __tablename__ = 'site_shifts'

    # Table columns
    y = Column(Integer)
    x = Column(Integer)
    site_id = Column(Integer, ForeignKey('sites.id'))
    cycle_id = Column(Integer, ForeignKey('cycles.id'))

    # Relationships to other tables
    site = relationship(
        'Site',
        backref=backref('shifts', cascade='all, delete-orphan')
    )
    cycle = relationship(
        'Cycle',
        backref=backref('site_shifts', cascade='all, delete-orphan')
    )

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

    #: str: name of the corresponding database table
    __tablename__ = 'site_intersections'

    # Table columns
    upper_overhang = Column(Integer)
    lower_overhang = Column(Integer)
    right_overhang = Column(Integer)
    left_overhang = Column(Integer)
    site_id = Column(Integer, ForeignKey('sites.id'))

    # Relationships to other tables
    site = relationship(
        'Site',
        backref=backref(
            'intersection', uselist=False, cascade='all, delete-orphan'
        )
    )

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
