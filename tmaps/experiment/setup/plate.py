import os.path as p

from werkzeug import secure_filename

from tmlib import plate as tmlib_plate

from tmaps.extensions import db
from tmaps.model.decorators import auto_remove_directory, auto_create_directory
from tmaps.experiment import Experiment


def _plate_loc(name, experiment_id):
    sec_name = secure_filename(name)
    e = Experiment.query.get(experiment_id)
    dirname = tmlib_plate.Plate.PLATE_DIR_FORMAT.format(name=sec_name)
    return p.join(e.plate_sources_location, dirname)


@auto_create_directory(lambda t: _plate_loc(t.name, t.experiment_id))
@auto_remove_directory(lambda pl: pl.location)
class Plate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), index=True)
    description = db.Column(db.Text)

    experiment_id = db.Column(db.Integer, db.ForeignKey('experiment.id'))

    experiment = db.relationship('Experiment', backref='plates')

    created_on = db.Column(db.DateTime, default=db.func.now())

    def __init__(self, name, description, experiment):
        self.name = name
        self.description = description
        self.experiment_id = experiment.id

    @property
    def location(self):
        return plates_location(self.name, self.experiment_id)

    @property
    def is_ready_for_processing(self):
        # TODO
        return False

    def as_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description
        }
