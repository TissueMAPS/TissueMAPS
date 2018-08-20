# TmLibrary - TissueMAPS library for distibuted image analysis routines.
# Copyright (C) 2016-2018 University of Zurich.
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
import logging
import numpy as np
from sqlalchemy import Column, Integer, ForeignKey, Boolean
from sqlalchemy.orm import relationship, backref
from sqlalchemy import UniqueConstraint

from tmlib.models.base import ExperimentModel, IdMixIn


logger = logging.getLogger(__name__)


class Site(ExperimentModel, IdMixIn):

    '''A *site* is a unique `y`, `x` position projected onto the
    *plate* bottom plane that was scanned by the microscope.

    Attributes
    ----------
    shifts: [tmlib.models.alignment.SiteShifts]
        shifts belonging to the site
    channel_image_files: List[tmlib.models.file.ChannelImageFile]
        channel image files belonging to the site
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

    #: number of pixels that should be cropped at the bottom for alignment
    bottom_residue = Column(Integer)

    #: number of pixels that should be cropped at the top for alignment
    top_residue = Column(Integer)

    #: number of pixels that should be cropped at the left side for alignment
    left_residue = Column(Integer)

    #: number of pixels that should be cropped at the right side for alignment
    right_residue = Column(Integer)

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
        self.bottom_residue = 0
        self.top_residue = 0
        self.left_residue = 0
        self.right_residue = 0

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
    def aligned_image_size(self):
        '''Tuple[int]: number of pixels along the vertical (*y*) and horizontal
        (*x*) axis, i.e. height and width of the aligned site
        '''
        return (self.aligned_height, self.aligned_width)

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

    @property
    def aligned_height(self):
        '''int: number of pixels along the vertical axis of the site after
        alignment between cycles
        '''
        return self.height - (self.top_residue + self.bottom_residue)

    @property
    def aligned_width(self):
        '''int: number of pixels along the horizontal axis of the site after
        alignment between cycles
        '''
        return self.width - (self.right_residue + self.left_residue)

    @property
    def aligned_offset(self):
        '''Tuple[int]: *y*, *x* coordinate of the top, left corner of the site
        relative to the layer overview at the maximum zoom level after
        alignment for shifts between cycles
        '''
        y_offset, x_offset = self.offset
        return (y_offset + self.top_residue, x_offset + self.left_residue)

    def __repr__(self):
        return (
            '<Site(id=%r, well_id=%r, y=%r, x=%r)>'
            % (self.id, self.well_id, self.y, self.x)
        )
