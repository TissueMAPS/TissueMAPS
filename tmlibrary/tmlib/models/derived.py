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
import shutil
from sqlalchemy import (
    Column, String, Integer, BigInteger, ForeignKey,
    UniqueConstraint, PrimaryKeyConstraint
)
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship, backref

from tmlib.utils import autocreate_directory_property, create_directory
from tmlib.models.base import (
    DirectoryModel, IdMixIn
)
from tmlib.models.utils import remove_location_upon_delete


logger = logging.getLogger(__name__)

#: Format string for channel locations
DERIVED_IMAGE_LOCATION_FORMAT = 'derived_image_{id}'


@remove_location_upon_delete
class DerivedImageType(DirectoryModel, IdMixIn):

    '''A *derived image type* represents a conceptual group of
    *derived images* that reflect different image types.

    Attributes
    ----------
    image_files: List[tmlib.models.file.DerivedImageFile]
        images belonging to the derived image type
    '''

    __tablename__ = 'derived_image_types'

    __table_args__ = (UniqueConstraint('name'), )

    #: str: name given by user
    name = Column(String(50), index=True, nullable=False)

    #: int: number of bytes used to encode intensity
    bit_depth = Column(Integer)

    #: int: ID of parent experiment
    experiment_id = Column(
        Integer,
        ForeignKey('experiment.id', onupdate='CASCADE', ondelete='CASCADE'),
        index=True
    )

    #: tmlib.models.experiment.Experiment: parent experiment
    experiment = relationship(
        'Experiment',
        backref=backref('derived_image_types', cascade='all, delete-orphan')
    )

    def __init__(self, name, bit_depth, experiment_id):
        '''
        Parameters
        ----------
        name: str
            name of the derived image type, e.g. "volume image"
        bit_depth: int
            number of bits used to indicate intensity of pixels
        experiment_id: int
            ID of the parent
            :class:`Experiment <tmlib.models.experiment.Experiment>`
        '''
        self.name = name
        self.bit_depth = bit_depth
        self.experiment_id = experiment_id

    @hybrid_property
    def location(self):
        '''str: location were derived_images are is stored'''
        if self._location is None:
            if self.id is None:
                raise AttributeError(
                    'DerivedImage "%s" doesn\'t have an entry in the database yet. '
                    'Therefore, its location cannot be determined.' % self.name
                )
            self._location = os.path.join(
                self.experiment.derived_images_location,
                DERIVED_IMAGE_LOCATION_FORMAT.format(
                    id=self.derivedimage_type_id
                )
            )
            if not os.path.exists(self._location):
                logger.debug(
                    'create location for derived image "%s": %s',
                    self.name, self._location
                )
                create_directory(self._location)
        return self._location

    @autocreate_directory_property
    def image_files_location(self):
        '''str: location where image files are stored'''
        return os.path.join(self.location, 'images')

    def get_image_file_location(self, image_file_id):
        # TODO: It's not ideal to store them all in one directory. While modern
        # filesystems are able to handle this relatively well we should get
        # better performance using subdirectories.
        # Use a hash function to map image ID to subdirectory.
        return self.image_files_location

    def remove_image_files(self):
        '''Removes all image files on disk'''
        # TODO: walk sudirectories and delete all files
        shutil.rmtree(self.image_files_location)




