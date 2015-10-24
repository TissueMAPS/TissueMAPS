import os
import os.path as p
from sqlalchemy import event
from werkzeug import secure_filename
from ..extensions.database import db
from utils import auto_remove_directory, auto_create_directory
from tmaps.models import Experiment


def _get_dirpath(id, name, prefix):
    """Return the directory path for a model with `id` and `name` and prepend
    the path `prefix`"""
    dirname = secure_filename(name)
    return p.join(prefix, '%d__%s' % (id, dirname))


def _get_dirpath_for_plate(id, name, experiment):
    """Return the directory path for a plate"""
    return _get_dirpath(id, name, experiment.plates_location)


def _get_dirpath_for_plate_target(plate_target):
    """Return the directory path for a plate target.
    A plate target is a plate object without access to relationship objects."""
    # Get the experiment manually since plate.experiment is not yet available
    e = Experiment.query.get(plate_target.experiment_id)
    return _get_dirpath_for_plate(plate_target.id, plate_target.name, e)


def _get_dirpath_for_acquisition(id, name, plate):
    """Return the directory path for a acquisition"""
    return _get_dirpath(id, name, plate.location)


def _get_dirpath_for_acquisition_target(acquisition_target):
    """Return the directory path for a acquisition target.
    A acquisition target is an acquisition object without access to relationship objects."""
    # Get the plate manually since acquisition.plate is not yet available
    pl = Plate.query.get(acquisition_target.plate_id)
    return _get_dirpath_for_acquisition(
        acquisition_target.id, acquisition_target.name, pl)


@auto_create_directory(_get_dirpath_for_acquisition_target)
@auto_remove_directory(lambda target: target.location)
class Acquisition(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), index=True)
    description = db.Column(db.Text)

    plate_id = db.Column(db.Integer, db.ForeignKey('plate.id'))

    plate = db.relationship('Plate', backref='acquisitions')

    created_on = db.Column(db.DateTime, default=db.func.now())

    def __init__(self, name, description, plate):
        self.name = name
        self.description = description
        self.plate_id = plate.id

    @property
    def location(self):
        return _get_dirpath_for_acquisition(self.id, self.name, self.plate)

    def as_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description
        }


@auto_create_directory(_get_dirpath_for_plate_target)
@auto_remove_directory(lambda target: target.location)
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
        return _get_dirpath_for_plate(self.id, self.name, self.experiment)

    def as_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'acquisitions': [a.as_dict() for a in self.acquisitions]
        }
