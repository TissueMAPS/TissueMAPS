from geoalchemy2 import Geometry

from sqlalchemy import Column, String, Integer, Float, ForeignKey
from sqlalchemy.orm import relationship
import geoalchemy2.functions as geofunc

from tmlib.models.base import Model


class MapobjectType(Model):
    __tablename__ = 'mapobject_types'

    name = Column(String)
    min_poly_zoom = Column(Integer)

    experiment_id = Column(Integer, ForeignKey('experiments.id'))
    experiment = relationship('Experiment', backref='mapobject_types')

    def get_mapobject_outlines_within_tile(self, session, x, y, z, t, zplane):
        do_simplify = z < self.min_poly_zoom
        if do_simplify:
            select_stmt = session.query(
                MapobjectOutline.mapobject_id,
                MapobjectOutline.geom_centroid.ST_AsGeoJSON())
        else:
            select_stmt = session.query(
                MapobjectOutline.mapobject_id,
                MapobjectOutline.geom_poly.ST_AsGeoJSON())

        outlines = select_stmt.\
            join(MapobjectOutline.mapobject).\
            filter(
                (Mapobject.mapobject_type_id == self.id) &
                (MapobjectOutline.tpoint == t) &
                (MapobjectOutline.zplane == zplane) &
                (MapobjectOutline.intersection_filter(x, y, z))).\
            all()

        return outlines


class Mapobject(Model):
    __tablename__ = 'mapobjects'

    mapobject_type_id = Column(Integer, ForeignKey('mapobject_types.id'))
    mapobject_type = relationship(
        'MapobjectType', backref='mapobjects')


class MapobjectOutline(Model):
    __tablename__ = 'mapobject_outlines'

    tpoint = Column(Integer)
    zplane = Column(Integer)

    geom_poly = Column(Geometry('POLYGON'))
    geom_centroid = Column(Geometry('POINT'))

    mapobject_id = Column(Integer, ForeignKey('mapobjects.id'))
    mapobject = relationship('Mapobject', backref='outlines')

    @staticmethod
    def intersection_filter(x, y, z):
        size = 256 * 2 ** (6 - z)
        x0 = x * size
        y0 = y * size

        minx = x0
        maxx = x0 + size
        miny = -y0 - size
        maxy = -y0

        tile = 'POLYGON(({maxx} {maxy},{minx} {maxy}, {minx} {miny}, {maxx} {miny}, {maxx} {maxy}))'.format(
            minx=minx,
            maxx=maxx,
            miny=miny,
            maxy=maxy)
        top_border = 'LINESTRING({minx} {miny}, {maxx} {miny})'.format(
            minx=minx,
            maxx=maxx,
            miny=miny)
        left_border = 'LINESTRING({minx} {maxy}, {minx} {miny})'.format(
            minx=minx,
            maxy=maxy,
            miny=miny)

        tile_filter =  (
            (MapobjectOutline.geom_poly.ST_Intersects(tile)) &
            (~MapobjectOutline.geom_poly.ST_Intersects(left_border)) &
            (~MapobjectOutline.geom_poly.ST_Intersects(top_border)))

        return tile_filter


class Feature(Model):
    __tablename__ = 'features'

    name = Column(String)

    mapobject_type_id = Column(Integer, ForeignKey('mapobject_types.id'))
    mapobject_type = relationship('MapobjectType', backref='features')


class FeatureValue(Model):
    __tablename__ = 'feature_values'

    value = Column(Float(precision=15))
    tpoint = Column(Integer)

    feature_id = Column(Integer, ForeignKey('features.id'))
    feature = relationship('Feature', backref='values')

    mapobject_id = Column(Integer, ForeignKey('mapobjects.id'))
    mapobject = relationship('Mapobject', backref='feature_values')
