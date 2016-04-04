import logging
import numpy as np
from cached_property import cached_property
from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship, backref
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
    well = relationship(
        'Well',
        backref=backref('sites', cascade='all, delete-orphan')
    )

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

    @cached_property
    def offset(self):
        '''Tuple[int]: *y*, *x* coordinate of the top, left corner of the site
        relative to the layer overview at the maximum zoom level
        '''
        well = self.well
        plate = well.plate
        n_rows = plate.nonempty_rows.index(well.coordinate[0])
        n_columns = plate.nonempty_columns.index(well.coordinate[1])
        experiment = plate.experiment
        plate_coordinate = tuple(
            [a[0] for a in np.where(experiment.plate_grid == plate.id)]
        )
        # NOTE: Shifts of sites between cycles only affect pixels within the
        # site and are therefore handled separately.
        y_offset = (
            # Sites in the well above the site
            self.coordinate[0] * self.image_size[0] +
            # Potential displacement of sites in y-direction
            self.coordinate[0] * experiment.vertical_site_displacement +
            # Wells in the plate above the well
            n_rows * well.image_size[0] +
            # Gaps introduced between wells
            n_rows * experiment.well_spacer_size +
            # Plates above the plate
            plate_coordinate[0] * plate.image_size[0] +
            # Gaps introduced between plates
            plate_coordinate[0] * experiment.plate_spacer_size
        )
        x_offset = (
            # Sites in the well left of the site
            self.coordinate[1] * self.image_size[1] +
            # Potential displacement of sites in y-direction
            self.coordinate[1] * experiment.horizontal_site_displacement +
            # Wells in the plate left of the well
            n_columns * well.image_size[1] +
            # Gaps introduced between wells
            n_columns * experiment.well_spacer_size +
            # Plates left of the plate
            plate_coordinate[1] * plate.image_size[0] +
            # Gaps introduced between plates
            plate_coordinate[1] * experiment.plate_spacer_size
        )
        return (y_offset, x_offset)

    def __repr__(self):
        return (
            '<Site(id=%r, well=%r, y=%r, x=%r)>'
            % (self.id, self.well.name, self.y, self.x)
        )
