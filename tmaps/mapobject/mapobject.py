from geoalchemy2 import Geometry

from tmaps.extensions.database import db
from tmaps.model import Model, CRUDMixin
from sqlalchemy import and_
import geoalchemy2.functions as geofunc


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


class MapobjectOutline(Model):
    __tablename__ = 'mapobject_outline'

    id = db.Column(db.Integer, primary_key=True)

    time = db.Column(db.Integer)
    z_level = db.Column(db.Integer)

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
    def get_mapobject_outlines_within_tile(mapobject_name, x, y, z, t, zlevel):
            return db.session.\
            query(
                MapobjectOutline.mapobject_id,
                MapobjectOutline.geom_poly.ST_NPoints(),
                MapobjectOutline.geom_poly.ST_AsGeoJSON(),
                MapobjectOutline.geom_centroid.ST_AsGeoJSON()).\
            join(MapobjectOutline.mapobject).\
            filter(
                (Mapobject.name == mapobject_name) &
                (MapobjectOutline.time == t) &
                (MapobjectOutline.z_level == zlevel) &
                (MapobjectOutline.intersection_filter(x, y, z))
            ).all()

