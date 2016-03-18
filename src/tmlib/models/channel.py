import os.path as p
from xml.dom import minidom

from sqlalchemy import Column, String, Integer, ForeignKey
from sqlalchemy.orm import relationship

from tmlib.models.base import Model


class Channel(Model):
    __tablename__ = 'channels'

    name = Column(String)

    experiment_id = Column(Integer, ForeignKey('experiments.id'))
    experiment = relationship('Experiment', backref='channels')

    @property
    def location(self):
        return p.join(self.experiment.channels_location, self.name)

    def as_dict(self):
        return {
            'id': self.hash,
            'name': self.name,
            'layers': [l.as_dict() for l in self.layers]
        }


class ChannelLayer(Model):
    __tablename__ = 'channel_layers'

    zplane = Column(Integer)
    tpoint = Column(Integer)

    channel_id = Column(Integer, ForeignKey('channels.id'))
    channel = relationship('Channel', backref='layers')

    @property
    def location(self):
        return p.join(
            self.channel.location, 'layer_z%03d_t%05d'
            % (self.zplane, self.tpoint))

    @property
    def image_size(self):
        metainfo_file = p.join(self.location, 'ImageProperties.xml')
        with open(metainfo_file, 'r') as f:
            dom = minidom.parse(f)
            width = int(dom.firstChild.getAttribute('WIDTH'))
            height = int(dom.firstChild.getAttribute('HEIGHT'))
            return (width, height)

    def as_dict(self):
        image_width, image_height = self.image_size
        return {
            'id': self.hash,
            'zplane': self.zplane,
            'tpoint': self.tpoint,
            'imageSize': {
                'width': image_width,
                'height': image_height
            }
        }
