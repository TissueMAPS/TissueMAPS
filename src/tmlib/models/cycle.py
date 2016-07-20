import os
import logging
from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship, backref
from sqlalchemy import UniqueConstraint

from tmlib.models import Model, DateMixIn
from tmlib.models import distribute_by
from tmlib.models.utils import remove_location_upon_delete
from tmlib.utils import autocreate_directory_property

logger = logging.getLogger(__name__)

#: Format string for acquisition locations
CYCLE_LOCATION_FORMAT = 'cycle_{id}'


@remove_location_upon_delete
@distribute_by('id')
class Cycle(Model, DateMixIn):

    '''A *cycle* represents an individual image acquisition time point.
    In case of a time series experiment, *cycles* have different time point,
    but the same channel indices, while in case of a "multiplexing"
    experiment, they have the same time point, but different channel indices.

    Attributes
    ----------
    index: int
        index of the cycle (based on the order of acquisition)
    tpoint: int
        time point of the cycle
    plate_id: int
        ID of the parent plate
    plate: tmlib.models.Plate
        parent plate to which the cycle belongs
    channel_image_files: List[tmlib.models.ChannelImageFile]
        channel image files that belong to the cycle
    site_shifts: List[tmlib.models.SiteShift]
        shifts that belong to the cycle
    '''

    #: str: name of the corresponding database table
    __tablename__ = 'cycles'

    __table_args__ = (UniqueConstraint('tpoint', 'index', 'plate_id'), )

    # Table columns
    tpoint = Column(Integer, index=True)
    index = Column(Integer, index=True)
    plate_id = Column(
        Integer,
        ForeignKey('plates.id', onupdate='CASCADE', ondelete='CASCADE'),
        index=True
    )

    # Relationships to other tables
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
        '''str: location were the acquisition content is stored'''
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
