from geoalchemy2 import Geometry

from tmaps.extensions.database import db
from tmaps.model import Model, CRUDMixin
from sqlalchemy import and_
import geoalchemy2.functions as geofunc



class MapobjectType(Model):
    __tablename__ = 'mapobject_type'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120))

    experiment_id = db.Column(db.Integer, db.ForeignKey('experiment.id'))
    experiment = db.relationship('Experiment', backref='mapobject_types')


class Mapobject(Model):
    __tablename__ = 'mapobject'

    id = db.Column(db.Integer, primary_key=True)
    external_id = db.Column(db.Integer, index=True)
    mapobject_type_id = db.Column(db.Integer, db.ForeignKey('mapobject_type.id'))
    mapobject_type = db.relationship(
        'MapobjectType', backref='mapobjects')

    @staticmethod
    def translate_external_ids(external_ids, experiment_id, mapobject_name):
        mapobjects = db.session.\
            query(Mapobject).\
            join(MapobjectType).\
            filter(
                (Mapobject.external_id.in_(external_ids)) &
                (MapobjectType.experiment_id == experiment_id) &
                (MapobjectType.name == mapobject_name)
            ).all()
        ids = [o.id for o in mapobjects]
        return ids


class MapobjectOutline(Model):
    __tablename__ = 'mapobject_outline'

    id = db.Column(db.Integer, primary_key=True)

    tpoint = db.Column(db.Integer)
    zplane = db.Column(db.Integer)

    geom_poly = db.Column(Geometry('POLYGON'))
    geom_centroid = db.Column(Geometry('POINT'))

    mapobject_id = db.Column(db.Integer, db.ForeignKey('mapobject.id'))
    mapobject = db.relationship('Mapobject', backref='outlines')

    @staticmethod
    def intersection_filter(x, y, z):
        size = 256 * 2 ** (6 - z)
        x0 = x * size
        y0 = y * size

        minx = x0
        maxx = x0 + size
        miny = -y0 - size
        maxy = -y0

        tile = 'LINESTRING({maxx} {maxy},{minx} {maxy}, {minx} {miny}, {maxx} {miny}, {maxx} {maxy})'.format(
            minx=minx,
            maxx=maxx,
            miny=miny,
            maxy=maxy
        )

        return MapobjectOutline.geom_poly.intersects(tile)

    @staticmethod
    def get_mapobject_outlines_within_tile(mapobject_name, x, y, z, t, zplane):
        return db.session.\
        query(
            MapobjectOutline.mapobject_id,
            MapobjectOutline.geom_poly.ST_NPoints(),
            MapobjectOutline.geom_poly.ST_AsGeoJSON(),
            MapobjectOutline.geom_centroid.ST_AsGeoJSON()).\
        join(MapobjectOutline.mapobject).\
        join(MapobjectType).\
        filter(
            (MapobjectType.name == mapobject_name) &
            (MapobjectOutline.tpoint == t) &
            (MapobjectOutline.zplane == zplane) &
            (MapobjectOutline.intersection_filter(x, y, z))
        ).all()


class Feature(Model):

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120))

    mapobject_type_id = db.Column(db.Integer, db.ForeignKey('mapobject_type.id'))
    mapobject_type = db.relationship('MapobjectType', backref='features')


class FeatureValue(Model):

    id = db.Column(db.Integer, primary_key=True)
    value = db.Column(db.Float(precision=15))
    tpoint = db.Column(db.Integer)

    feature_id = db.Column(db.Integer, db.ForeignKey('feature.id'))
    feature = db.relationship('Feature', backref='values')

    mapobject_id = db.Column(db.Integer, db.ForeignKey('mapobject.id'))
    mapobject = db.relationship('Mapobject', backref='feature_values')
