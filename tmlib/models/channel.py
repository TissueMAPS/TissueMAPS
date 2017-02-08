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
from sqlalchemy import Column, Integer, String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship, backref
from sqlalchemy.ext.hybrid import hybrid_property

from tmlib.models.base import DirectoryModel, DateMixIn
from tmlib.utils import autocreate_directory_property, create_directory
from tmlib.models.utils import remove_location_upon_delete

logger = logging.getLogger(__name__)

#: Format string for channel locations
CHANNEL_LOCATION_FORMAT = 'channel_{id}'


@remove_location_upon_delete
class Channel(DirectoryModel, DateMixIn):

    '''A *channel* represents all *images* across different time points and
    spatial positions that were acquired with the same illumination and
    microscope filter settings.

    Attributes
    ----------
    image_files: List[tmlib.models.file.ChannelImageFile]
        images belonging to the channel
    layers: List[tmlib.models.layer.ChannelLayer]
        layers belonging to the channel
    '''

    __tablename__ = 'channels'

    __table_args__ = (UniqueConstraint('name'), UniqueConstraint('index'))

    #: str: name given by the microscope or user
    name = Column(String, index=True)

    #: int: zero-based channel index
    index = Column(Integer, index=True)

    #: str: name of wavelength
    wavelength = Column(String, index=True)

    #: int: number of bytes used to encode intensity
    bit_depth = Column(Integer)

    #: int: ID of the parent experiment
    experiment_id = Column(
        Integer,
        ForeignKey('experiment.id', onupdate='CASCADE', ondelete='CASCADE'),
        index=True
    )

    #: tmlib.models.experiment.Experiment: parent experiment
    experiment = relationship(
        'Experiment',
        backref=backref('channels', cascade='all, delete-orphan')
    )

    def __init__(self, name, index, wavelength, bit_depth, experiment_id):
        '''
        Parameters
        ----------
        name: str
            name of the channel
        index: int
            zero-based channel index
        wavelength: str
            name of the corresponding wavelength
        bit_depth: int
            number of bits used to indicate intensity of pixels
        experiment_id: int
            ID of the parent
            :class:`Experiment <tmlib.models.experiment.Experiment>`
        '''
        self.name = name
        self.index = index
        self.wavelength = wavelength
        self.bit_depth = bit_depth
        self.experiment_id = experiment_id

    @hybrid_property
    def location(self):
        '''str: location were cycle content is stored'''
        if self._location is None:
            if self.id is None:
                raise AttributeError(
                    'Channel "%s" doesn\'t have an entry in the database yet. '
                    'Therefore, its location cannot be determined.' % self.name
                )
            self._location = os.path.join(
                self.experiment.channels_location,
                CHANNEL_LOCATION_FORMAT.format(id=self.id)
            )
            if not os.path.exists(self._location):
                logger.debug(
                    'create location for channel "%s": %s',
                    self.name, self._location
                )
                create_directory(self._location)
        return self._location

    @autocreate_directory_property
    def images_location(self):
        '''str: location where image files are stored'''
        return os.path.join(self.location, 'images')

    @autocreate_directory_property
    def illumstats_location(self):
        '''str: location where illumination statistics files are stored'''
        return os.path.join(self.location, 'illumstats')

    def __repr__(self):
        return '<Channel(id=%r, name=%r)>' % (self.id, self.name)
