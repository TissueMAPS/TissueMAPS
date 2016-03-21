import os
import logging
from xml.dom import minidom
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

from tmlib.models.base import Model
from tmlib.models.utils import auto_create_directory
from tmlib.models.utils import auto_remove_directory
from ..utils import autocreate_directory_property

logger = logging.getLogger(__name__)

#: Format string for channel locations
CHANNEL_LOCATION_FORMAT = 'channel_{id}'

#: Format string for channel layer locations
# TODO: Should this be renamed to layer_XX?
CHANNEL_LAYER_LOCATION_FORMAT = 'layer_{id}'


@auto_remove_directory(lambda obj: obj.location)
@auto_create_directory(lambda obj: obj.location)
class Channel(Model):

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
    '''

    #: Name of the corresponding database table
    __tablename__ = 'channels'

    #: Table columns
    name = Column(String, index=True)
    experiment_id = Column(Integer, ForeignKey('experiments.id'))

    #: Relationships to other tables
    experiment = relationship('Experiment', backref='channels')

    def __init__(self, name, experiment):
        '''
        Parameters
        ----------
        name: str
            name of the plate
        experiment: tmlib.models.Experiment
            parent experiment to which the plate belongs
        '''
        self.name = name
        self.experiment = experiment
        self.experiment_id = experiment.id

    @property
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


class ChannelLayer(Model):

    '''A *channel layer* represents a pyramid with an overview of all images
    belonging to a given *channel*, time point, and z-plane at different
    resolution levels.

    Attributes
    ----------
    tpoint: int
        time point index
    zplane: int
        z-plane index
    channel_id: int
        ID of the parent channel
    channel: tmlib.models.Channel
        parent channel to which the plate belongs
    '''

    #: Name of the corresponding database table
    __tablename__ = 'channel_layers'

    #: Table columns
    tpoint = Column(Integer)
    zplane = Column(Integer)
    channel_id = Column(Integer, ForeignKey('channels.id'))

    #: Relationships to other tables
    channel = relationship('Channel', backref='layers')

    def __init__(self, tpoint, zplane, channel):
        '''
        Parameters
        ----------
        tpoint: int
            time point index
        zplane: int
            z-plane index
        channel: tmlib.models.Channel
            channel object to which the plate belongs
        '''
        self.tpoint = tpoint
        self.zplane = zplane
        self.channel_id = channel.id

    @property
    def location(self):
        '''str: location were the acquisition content is stored'''
        if self.id is None:
            raise AttributeError(
                'Channel layer "%s" doesn\'t have an entry in the database yet. '
                'Therefore, its location cannot be determined.' % self.name
            )
        return os.path.join(
            self.channel.layers_location,
            CHANNEL_LAYER_LOCATION_FORMAT.format(id=self.id)
        )

    @property
    def image_size(self):
        '''Tuple[int]: number of pixels along the y and x axis at the highest
        zoom level
        '''
        metainfo_file = os.path.join(self.location, 'ImageProperties.xml')
        with open(metainfo_file, 'r') as f:
            dom = minidom.parse(f)
            width = int(dom.firstChild.getAttribute('WIDTH'))
            height = int(dom.firstChild.getAttribute('HEIGHT'))
        return (height, width)

    # TODO: pyramid creation

    def as_dict(self):
        '''
        Return attributes as key-value pairs.

        Returns
        -------
        dict
        '''
        image_height, image_width = self.image_size
        return {
            'id': self.hash,
            'zplane': self.zplane,
            'tpoint': self.tpoint,
            'image_size': {
                'width': image_width,
                'height': image_height
            }
        }

    def __repr__(self):
        return (
            '<ChannelLayer(id=%r, channel=%r, tpoint=%r, zplane=%r)>'
            % (self.id, self.channel_id, self.tpoint, self.zplane)
        )
