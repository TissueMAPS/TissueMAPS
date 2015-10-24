import os
import os.path as p
from xml.dom import minidom
from ..extensions.database import db
from utils import auto_generate_hash

# EXPERIMENT_ACCESS_LEVELS = (
#     'read',
#     'delete'
# )


class ExperimentShare(db.Model):
    recipient_user_id = db.Column(db.Integer, db.ForeignKey('user.id'),
                                  primary_key=True)
    donor_user_id = db.Column(db.Integer, db.ForeignKey('user.id'),
                              primary_key=True)
    experiment_id = db.Column(db.Integer, db.ForeignKey('experiment.id'),
                              primary_key=True)
    experiment = db.relationship('Experiment', uselist=False)
    # access_level = db.Column(db.Enum(*EXPERIMENT_ACCESS_LEVELS,
    #                                  name='access_level'))


@auto_generate_hash
class Experiment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    hash = db.Column(db.String(20))
    name = db.Column(db.String(120), index=True)
    location = db.Column(db.String(600))
    description = db.Column(db.Text)

    # layer_image_width = db.Column(db.Integer, nullable=False)
    # layer_image_height = db.Column(db.Integer, nullable=False)

    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_on = db.Column(db.DateTime, default=db.func.now())
    owner = db.relationship('User', backref='experiments')

    def __init__(self, name, location, description, owner_id):
        self.name = name
        if not p.isabs(location):
            raise ValueError(
                'The experiments location on the filesystem must be '
                'an absolute path'
            )
        self.location = location
        self.description = description
        self.owner_id = owner_id

    @property
    def dataset_path(self):
        return os.path.join(self.location, 'data.h5')

    @property
    def plates_location(self):
        return os.path.join(self.location, 'plates')

    def belongs_to(self, user):
        return self.owner == user

    @property
    def dataset(self):
        import h5py
        fpath = self.dataset_path
        if os.path.exists(fpath):
            print 'LOADING DATA SET'
            print fpath
            return h5py.File(fpath, 'r')
        else:
            return None

    def __repr__(self):
        return '<Experiment %r>' % self.name

    @property
    def layers(self):
        layers_dir = p.join(self.location, 'layers')
        layer_names = [name for name in os.listdir(layers_dir)
                       if p.isdir(p.join(layers_dir, name))]

        layers = []

        for layer_name in layer_names:
            layer_dir = p.join(layers_dir, layer_name)
            metainfo_file = p.join(layer_dir, 'ImageProperties.xml')

            if p.exists(metainfo_file):
                with open(metainfo_file, 'r') as f:
                    dom = minidom.parse(f)
                    width = int(dom.firstChild.getAttribute('WIDTH'))
                    height = int(dom.firstChild.getAttribute('HEIGHT'))

                    pyramid_path = '/experiments/{id}/layers/{name}/'.format(
                            id=self.hash, name=layer_name)

                    layers.append({
                        'name': layer_name,
                        'imageSize': [width, height],
                        'pyramidPath': pyramid_path
                    })

        return layers

    def as_dict(self):
        return {
            'id': self.hash,
            'name': self.name,
            'description': self.description,
            'owner': self.owner.name,
            'layers': self.layers
        }
