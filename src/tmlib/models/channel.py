import os
import logging
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

from tmlib.models.base import Model, DateMixIn
from tmlib.models.utils import auto_remove_directory
from tmlib.utils import autocreate_directory_property

logger = logging.getLogger(__name__)

#: Format string for channel locations
CHANNEL_LOCATION_FORMAT = 'channel_{id}'


@auto_remove_directory(lambda obj: obj.location)
class Channel(Model, DateMixIn):

    '''A *channel* represents all *images* across different time points and
    spatial positions that were acquired with the same illumination and
    microscope filter settings.

    Attributes
    ----------
    name: str
        name of the plate
    experiment_id: int
        ID of the parent experiment
    experiment: tmlib.models.Experiment
        parent experiment to which the plate belongs
    layers: List[tmlib.models.ChannelLayer]
        layers belonging to the channel
    illumstats_files: List[tmlib.model.IllumstatsFile]
        illumination statistics files that belongs to the channel
    '''

    #: str: name of the corresponding database table
    __tablename__ = 'channels'

    # Table columns
    name = Column(String, index=True)
    index = Column(Integer, index=True)
    experiment_id = Column(Integer, ForeignKey('experiments.id'))

    # Relationships to other tables
    experiment = relationship('Experiment', backref='channels')

    def __init__(self, name, index, experiment_id):
        '''
        Parameters
        ----------
        name: str
            name of the channel
        index: int
            zero-based channel index
        experiment_id: int
            ID of the parent experiment
        '''
        self.name = name
        self.index = index
        self.experiment_id = experiment_id

    @autocreate_directory_property
    def location(self):
        '''str: location were the channel content is stored'''
        if self.id is None:
            raise AttributeError(
                'Channel "%s" doesn\'t have an entry in the database yet. '
                'Therefore, its location cannot be determined.' % self.name
            )
        return os.path.join(
            self.experiment.channels_location,
            CHANNEL_LOCATION_FORMAT.format(id=self.id)
        )

    @autocreate_directory_property
    def layers_location(self):
        '''str: location where layers are stored'''
        return os.path.join(self.location, 'layers')

    def __repr__(self):
        return '<Channel(id=%r, name=%r)>' % (self.id, self.name)

    def as_dict(self):
        '''
        Return attributes as key-value pairs.

        Returns
        -------
        dict
        '''
        return {
            'id': self.id,
            'name': self.name,
            'layers': [l.as_dict() for l in self.layers]
        }
