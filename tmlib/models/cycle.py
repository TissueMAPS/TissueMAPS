import os
import logging
from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship, backref
from sqlalchemy import UniqueConstraint

from tmlib.models.base import DirectoryModel, DateMixIn
from tmlib.models.utils import remove_location_upon_delete
from tmlib.utils import autocreate_directory_property

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

    @autocreate_directory_property
    def location(self):
        '''str: location were cycle content is stored'''
        if self.id is None:
            raise AttributeError(
                'Cycle "%s" doesn\'t have an entry in the database yet. '
                'Therefore, its location cannot be determined.' % self.name
            )
        return os.path.join(
            self.plate.cycles_location,
            CYCLE_LOCATION_FORMAT.format(id=self.id)
        )

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
