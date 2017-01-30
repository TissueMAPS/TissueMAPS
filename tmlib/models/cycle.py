# TmLibrary - TissueMAPS library for distibuted image analysis routines.
# Copyright (C) 2016  Markus D. Herrmann, University of Zurich and Robin Hafen
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
import os
import logging
from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship, backref
from sqlalchemy import UniqueConstraint
from sqlalchemy.ext.hybrid import hybrid_property

from tmlib.models.base import DirectoryModel, DateMixIn
from tmlib.models.utils import remove_location_upon_delete
from tmlib.utils import autocreate_directory_property, create_directory

logger = logging.getLogger(__name__)

#: Format string for acquisition locations
CYCLE_LOCATION_FORMAT = 'cycle_{id}'


@remove_location_upon_delete
class Cycle(DirectoryModel, DateMixIn):

    '''A *cycle* represents an individual image acquisition time point.
    In case of a time series experiment, *cycles* have different time point,
    but the same channel indices, while in case of a "multiplexing"
    experiment, they have the same time point, but different channel indices.

    Attributes
    ----------
    channel_image_files: List[tmlib.models.file.ChannelImageFile]
        channel image files belonging to the cycle
    site_shifts: List[tmlib.models.site.SiteShift]
        shifts belonging to the cycle
    '''

    __tablename__ = 'cycles'

    __table_args__ = (UniqueConstraint('tpoint', 'index', 'plate_id'), )

    #: int: zero-based index in the time series
    tpoint = Column(Integer, index=True)

    #: int: zero-based index in the acquisition sequence
    index = Column(Integer, index=True)

    #: int: ID of parent plate
    plate_id = Column(
        Integer,
        ForeignKey('plates.id', onupdate='CASCADE', ondelete='CASCADE'),
        index=True
    )

    #: tmlib.models.plate.Plate: parent plate
    plate = relationship(
        'Plate',
        backref=backref('cycles', cascade='all, delete-orphan')
    )

    def __init__(self, index, tpoint, plate_id):
        '''
        Parameters
        ----------
        index: int
            index of the cycle (based on the order of acquisition)
        tpoint: int
            time point index
        plate_id: int
            ID of the parent plate
        '''
        self.index = index
        self.tpoint = tpoint
        self.plate_id = plate_id

    @hybrid_property
    def location(self):
        '''str: location were cycle content is stored'''
        if self._location is None:
            if self.id is None:
                raise AttributeError(
                    'Cycle "%s" doesn\'t have an entry in the database yet. '
                    'Therefore, its location cannot be determined.' % self.name
                )
            self._location = os.path.join(
                self.plate.cycles_location,
                CYCLE_LOCATION_FORMAT.format(id=self.id)
            )
            if not os.path.exists(self._location):
                logger.debug(
                    'create location for cycle #%d: %s',
                    self.index, self._location
                )
                create_directory(self._location)
        return self._location

    @autocreate_directory_property
    def channel_images_location(self):
        '''str: location where channel image files are stored'''
        return os.path.join(self.location, 'channel_images')

    @autocreate_directory_property
    def illumstats_location(self):
        '''str: location where illumination statistics files are stored'''
        return os.path.join(self.location, 'illumstats')

    def __repr__(self):
        return '<Cycle(id=%r, tpoint=%r)>' % (self.id, self.tpoint)
