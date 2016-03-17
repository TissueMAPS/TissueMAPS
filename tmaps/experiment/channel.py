import os.path as p
from xml.dom import minidom

from tmaps.extensions.database import db
from tmaps.model import HashIdModel


class Channel(HashIdModel):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120))

    experiment_id = db.Column(db.Integer, db.ForeignKey('experiment.id'))
    experiment = db.relationship('Experiment', backref='channels')

    @property
    def location(self):
        return p.join(self.experiment.channels_location, self.name)

    def as_dict(self):
        return {
            'id': self.hash,
            'name': self.name,
            'layers': [l.as_dict() for l in self.layers]
        }


class ChannelLayer(HashIdModel):
    id = db.Column(db.Integer, primary_key=True)

    zplane = db.Column(db.Integer)
    tpoint = db.Column(db.Integer)

    channel_id = db.Column(db.Integer, db.ForeignKey('channel.id'))
    channel = db.relationship('Channel', backref='layers')

    @property
    def location(self):
        return p.join(
            self.channel.location, 'layer_z%d_t%d'
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
