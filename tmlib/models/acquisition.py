import os
import logging
from sqlalchemy import Column, String, Integer, Text, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship, backref
from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import Session

from tmlib.models.base import DirectoryModel, ExperimentModel, DateMixIn
from tmlib.models.status import FileUploadStatus as fus
from tmlib.models.file import MicroscopeImageFile, MicroscopeMetadataFile
from tmlib.models.utils import remove_location_upon_delete
from tmlib.utils import autocreate_directory_property

logger = logging.getLogger(__name__)

#: Format string for acquisition locations
ACQUISITION_LOCATION_FORMAT = 'acquisition_{id}'


@remove_location_upon_delete
class Acquisition(DirectoryModel, DateMixIn):

    '''An *acquisition* contains all files belonging to one microscope image
    acquisition process. Note that in contrast to a *cycle*, an *acquisition*
    may contain more than one time point.

    The incentive to group files this way relates to the fact that most
    microscopes generate separate metadata files per *acquisition*.

    Attributes
    ----------
    microscope_image_files: List[tmlib.models.file.MicroscopeImageFile]
        microscope image files belonging to the acquisition
    microscope_metadata_files: List[tmlib.models.file.MicroscopeMetadataFile]
        microscope metadata files belonging to the acquisition
    image_file_mappings: List[tmlib.models.acquisition.ImageFileMapping]
        image file mappings belonging to the acquisition
    '''

    __tablename__ = 'acquisitions'

    __table_args__ = (UniqueConstraint('name', 'plate_id'), )

    #: str: name given by the user
    name = Column(String, index=True)

    #: str: description provided by the user
    description = Column(Text)

    #: int: ID of the parent plate
    plate_id = Column(
        Integer,
        ForeignKey('plates.id', onupdate='CASCADE', ondelete='CASCADE'),
        index=True
    )

    #: tmlib.models.plate.Plate: plate to which the acquisition belongs
    plate = relationship(
        'Plate',
        backref=backref('acquisitions', cascade='all, delete-orphan')
    )

    def __init__(self, name, plate_id, description=''):
        '''
        Parameters
        ----------
        name: str
            name of the acquisition
        plate_id: int
            ID of the parent plate
        description: str, optional
            description of the acquisition
        '''
        # TODO: ensure that name is unique within plate
        self.name = name
        self.description = description
        self.plate_id = plate_id

    @autocreate_directory_property
    def location(self):
        '''str: location were the acquisition content is stored'''
        if self.id is None:
            raise AttributeError(
                'Acquisition "%s" doesn\'t have an entry in the database yet. '
                'Therefore, its location cannot be determined.' % self.name
            )
        return os.path.join(
            self.plate.acquisitions_location,
            ACQUISITION_LOCATION_FORMAT.format(id=self.id)
        )

    @autocreate_directory_property
    def microscope_images_location(self):
        '''str: location where microscope image files are stored'''
        return os.path.join(self.location, 'microscope_images')

    @autocreate_directory_property
    def microscope_metadata_location(self):
        '''str: location where microscope metadata files are stored'''
        return os.path.join(self.location, 'microscope_metadata')

    @property
    def status(self):
        '''str: upload status based on the status of microscope files'''
        session = Session.object_session(self)
        img_files = session.query(MicroscopeImageFile.status).distinct()
        meta_files = session.query(MicroscopeMetadataFile.status).distinct()
        child_status = set([f.status for f in img_files]).\
            union([f.status for f in meta_files])
        if fus.UPLOADING in child_status:
            return fus.UPLOADING
        elif len(child_status) == 1 and fus.COMPLETE in child_status:
            return fus.COMPLETE
        else:
            return fus.WAITING

    def to_dict(self):
        '''Returns attributes as key-value pairs.

        Returns
        -------
        dict
        '''
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'status': self.status
        }

    def belongs_to(self, user):
        '''Determines whether the acquisition belongs to a given `user`.

        Parameters
        ----------
        user: tmlib.user.User
            `TissueMAPS` user

        Returns
        -------
        bool
            whether acquisition belongs to `user`
        '''
        return self.plate.belongs_to(user)

    def __repr__(self):
        return '<Acquisition(id=%r, name=%r)>' % (self.id, self.name)


class ImageFileMapping(ExperimentModel):

    '''Mapping of an individual 2D pixels plane to its location within one or
    more microscope image files. The nomenclature for image file content is
    based on the `OME data model <http://www.openmicroscopy.org/site/support/ome-model/>`_.

    See also
    --------
    :class:`tmlib.models.file.MicroscopeImageFile`
    :class:`tmlib.models.file.ChannelImageFile`

    '''

    __tablename__ = 'image_file_mappings'

    __distribute_by_hash__ = 'id'

    #: int: zero-based time point index in the time series
    tpoint = Column(Integer, index=True)

    #: int: number of bites used to encode intensity values
    bit_depth = Column(Integer)

    #: str: name of the wavelength
    wavelength = Column(String, index=True)

    #: dict: mapping of individual pixel plane to sub-file location
    map = Column(JSONB, index=True)

    #: int: ID of parent site
    site_id = Column(
        Integer,
        ForeignKey('sites.id', onupdate='CASCADE', ondelete='CASCADE'),
        index=True
    )

    #: int: ID of parent site
    cycle_id = Column(
        Integer,
        ForeignKey('cycles.id', onupdate='CASCADE', ondelete='CASCADE'),
        index=True
    )

    #: int: ID of parent acquisition
    acquisition_id = Column(
        Integer,
        ForeignKey('acquisitions.id', onupdate='CASCADE', ondelete='CASCADE'),
        index=True
    )

    #: int: ID of parent channel
    channel_id = Column(
        Integer,
        ForeignKey('channels.id', onupdate='CASCADE', ondelete='CASCADE'),
        index=True
    )

    #: tmlib.models.site.Site: parent site
    site = relationship(
        'Site',
        backref=backref('image_file_mappings', cascade='all, delete-orphan')
    )

    #: tmlib.models.acquisition.Acquisition: parent acquisition
    acquisition = relationship(
        'Acquisition',
        backref=backref('image_file_mappings', cascade='all, delete-orphan')
    )

    #: tmlib.models.cycle.Cycle: parent cycle
    cycle = relationship(
        'Cycle',
        backref=backref('image_file_mappings', cascade='all, delete-orphan')
    )

    #: tmlib.models.channel.Channel: parent channel
    channel = relationship(
        'Channel',
        backref=backref('image_file_mappings', cascade='all, delete-orphan')
    )

    def __init__(self, tpoint, wavelength, bit_depth, map, site_id,
                 acquisition_id, cycle_id=None, channel_id=None):
        '''
        Parameters
        ----------
        tpoint: int
            zero-based time point index in the time series
        wavelength: str
            name of the wavelength
        bit_depth: int
            number of bites used to indicate intensity
        map: dict
            maps an individual pixels plane to location(s) within microscope
            image files
        site_id: int
            ID of the parent site
        acquisition_id: int
            ID of the parent acquisition
        cycle_id: int, optional
            ID of the parent cycle (default: ``None``)
        channel_id: int, optional
            ID of the parent channel (default: ``None``)
        '''
        self.tpoint = tpoint
        self.wavelength = wavelength
        self.bit_depth = bit_depth
        self.map = map
        self.site_id = site_id
        self.acquisition_id = acquisition_id
        self.cycle_id = cycle_id
        self.channel_id = channel_id
