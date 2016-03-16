import os.path as p
from xml.dom import minidom

from tmaps.extensions.database import db
from tmaps.model import HashIdModel


class ChannelLayer(HashIdModel):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120))

    experiment_id = db.Column(db.Integer, db.ForeignKey('experiment.id'))
    experiment = db.relationship('Experiment', backref='layers')

    zplane = db.Column(db.Integer)
    tpoint = db.Column(db.Integer)

    created_on = db.Column(db.DateTime, default=db.func.now())

    @property
    def location(self):
        return p.join(self.experiment.layers_location, self.name)

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
            'name': self.name,
            'image_size': {
                'width': image_width,
                'height': image_height
            }
        }
