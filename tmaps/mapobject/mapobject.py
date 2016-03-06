from geoalchemy2 import Geometry

from tmaps.extensions.database import db
from tmaps.model import Model, CRUDMixin
from sqlalchemy import and_


class Mapobject(Model):
    __tablename__ = 'mapobject'

    id = db.Column(db.Integer, primary_key=True)
    external_id = db.Column(db.Integer, index=True)
    name = db.Column(db.String(120))

    @staticmethod
    def translate_external_ids(external_ids, experiment_id, mapobject_name):
        mapobjects = Mapobject.query.filter(
            (Mapobject.external_id.in_(external_ids)) &
            (Mapobject.experiment_id == experiment_id) &
            (Mapobject.name == mapobject_name)
        ).all()
        ids = [o.id for o in mapobjects]
        return ids

    experiment_id = db.Column(db.Integer, db.ForeignKey('experiment.id'))
    experiment = db.relationship(
        'Experiment', backref='mapobjects')


class MapobjectCoords(Model):
    __tablename__ = 'mapobject_coords'

    id = db.Column(db.Integer, primary_key=True)

    time = db.Column(db.Integer)
    z_level = db.Column(db.Integer)

    geom = db.Column(Geometry('POLYGON'))

    mapobject_id = db.Column(db.Integer, db.ForeignKey('mapobject.id'))
    mapobject = db.relationship('Mapobject', backref='coordinates')

