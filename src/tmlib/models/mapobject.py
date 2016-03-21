import logging
from geoalchemy2 import Geometry
from sqlalchemy import Column, String, Integer, Float, ForeignKey
from sqlalchemy.orm import relationship

from tmlib.models.base import Model

logger = logging.getLogger(__name__)


class MapobjectType(Model):

    '''A *map object type* represent a conceptual group of *map objects*
    (segmented objects) that reflect different biological entities,
    such as "cells" or "nuclei" for example.

    Attributes
    ----------
    name: str
        name of the map objects type
    min_poly_zoom: int
        zoom level where visualization should switch from centroids
        to outlines
    experiment_id: int
        ID of the parent experiment
    experiment: tmlib.models.Experiment
        parent experiment to which map objects belong
    '''

    #: Name of the corresponding database table
    __tablename__ = 'mapobject_types'

    #: Table columns
    name = Column(String)
    min_poly_zoom = Column(Integer)
    experiment_id = Column(Integer, ForeignKey('experiments.id'))

    #: Relationship to other tables
    experiment = relationship('Experiment', backref='mapobject_types')

    def __init__(self, name, min_poly_zoom, experiment):
        '''
        Parameters
        ----------
        name: str
            name of the map objects type, e.g. "cells"
        min_poly_zoom: int
            zoom level where visualization should switch from centroids
            to outlines
        experiment: tmlib.models.Experiment
            parent experiment to which map objects belong
        '''
        self.name = name
        self.min_poly_zoom = min_poly_zoom
        self.experiment_id = experiment.id

    def get_mapobject_outlines_within_tile(self, session, x, y, z, tpoint, zplane):
        '''Get outlines of all objects that fall within a given pyramid tile,
        defined by their `y`, `x`, `z` coordinates.

        Parameters
        ----------
        session: sqlalchemy.orm.session.Session
            database session
        x: int
            column map coordinate at the given `z` level
        y: int
            row map coordinate at the given `z` level
        z: int
            zoom level
        tpoint: int
            time point index
        zplane:
            z-plane index

        Returns
        -------
        Tuple[int, str]
            GeoJSON string for each selected map object
        '''
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
                (MapobjectOutline.tpoint == tpoint) &
                (MapobjectOutline.zplane == zplane) &
                (MapobjectOutline.intersection_filter(x, y, z))).\
            all()

        return outlines


class Mapobject(Model):

    '''
    An individual *map object* represents a connected pixel component in an
    image. They have coordinates that allows drawing their
    outlines on the map and may also be associated with measurements
    (*features*), which can be queried or used for analysis.

    Attributes
    ----------
    mapobject_type_id: int
        ID of the parent mapobject
    mapobject_type: tmlib.models.MapobjectType
        parent mapobject type to which map objects belong
    '''

    #: Name of the corresponding database table
    __tablename__ = 'mapobjects'

    #: Table columns
    mapobject_type_id = Column(Integer, ForeignKey('mapobject_types.id'))

    #: Relationships to other tables
    mapobject_type = relationship('MapobjectType', backref='mapobjects')

    def __init__(self, mapobject_type):
        '''
        Parameters
        ----------
        mapobject_type: tmlib.models.MapobjectType
            parent map object type to which map objects belong
        '''
        self.mapobject_type_id = mapobject_type.id


class MapobjectOutline(Model):

    '''Outlines of an individual *map object*.

    Attributes
    ----------
    tpoint: int
        time point index
    zplane: int
        z-plane index
    geom_poly: str
        EWKT polygon geometry
    geom_centroid: str
        EWKT point geometry
    mapobject_id: int
        ID of parent mapobject
    mapobject: tmlib.models.Mapobject
        parent mapobject to which the outline belongs
    '''

    #: Name of the corresponding database table
    __tablename__ = 'mapobject_outlines'

    #: Table columns
    tpoint = Column(Integer)
    zplane = Column(Integer)
    geom_poly = Column(Geometry('POLYGON'))
    geom_centroid = Column(Geometry('POINT'))
    mapobject_id = Column(Integer, ForeignKey('mapobjects.id'))

    #: Relationships to other tables
    mapobject = relationship('Mapobject', backref='mapobject_outlines')

    def __init__(self, tpoint, zplane, geom_poly, geom_centroid, mapobject):
        '''
        Parameters
        ----------
        tpoint: int
            time point index
        zplane: int
            z-plane index
        geom_poly: str
            EWKT polygon geometry
        geom_centroid: str
            EWKT point geometry
        mapobject: tmlib.models.Mapobject
            parent map object to which the outline belongs
        '''
        self.tpoint = tpoint
        self.zplane = zplane
        self.geom_poly = geom_poly
        self.geom_centroid = geom_centroid
        self.mapobject_id = mapobject.id

    @staticmethod
    def intersection_filter(x, y, z):
        '''
        Generate an `SQLalchemy` query filter to select mapobject outlines
        for a given `y`, `x`, `z` pyramid coordinate.

        Parameters
        ----------
        x: int
            column map coordinate at the given `z` level
        y: int
            row map coordinate at the given `z` level
        z: int
            zoom level

        Returns
        -------
        ???
        '''
        # TODO: docstring
        size = 256 * 2 ** (6 - z)
        x0 = x * size
        y0 = y * size

        minx = x0
        maxx = x0 + size
        miny = -y0 - size
        maxy = -y0

        tile = 'POLYGON(({maxx} {maxy},{minx} {maxy}, {minx} {miny}, {maxx} {miny}, {maxx} {maxy}))'.format(
            minx=minx, maxx=maxx, miny=miny, maxy=maxy
        )
        top_border = 'LINESTRING({minx} {miny}, {maxx} {miny})'.format(
            minx=minx, maxx=maxx, miny=miny
        )
        left_border = 'LINESTRING({minx} {maxy}, {minx} {miny})'.format(
            minx=minx, maxy=maxy, miny=miny
        )

        return (
            (MapobjectOutline.geom_poly.ST_Intersects(tile)) &
            (~MapobjectOutline.geom_poly.ST_Intersects(left_border)) &
            (~MapobjectOutline.geom_poly.ST_Intersects(top_border))
        )


class Feature(Model):

    '''A *feature* is a measurement that is associated with a particular
    *map object type*. For example the *feature* named "Morphology_Area"
    would correspond to a vector where each value would reflect the area of an
    individual *map object* of a given *map object type*.

    Attributes
    ----------
    name: str
        name of the feature
    mapobject_type_id: int
        ID of parent mapobject type
    mapobject_type: tmlib.models.MapobjectType
        parent map object type to which the feature belongs
    '''

    #: Name of the corresponding database table
    __tablename__ = 'features'

    #: Table columns
    name = Column(String)
    mapobject_type_id = Column(Integer, ForeignKey('mapobject_types.id'))

    #: Relationships to other tables
    mapobject_type = relationship('MapobjectType', backref='features')

    def __init__(self, name, mapobject_type):
        '''
        Parameters
        ----------
        name: str
            name of the feature
        mapobject_type: tmlib.models.MapobjectType
            parent map object type to which the feature belongs
        '''
        self.name = name
        self.mapobject_type_id = mapobject_type.id


class FeatureValue(Model):

    '''An individual value of a *feature* that was measured for a given
    *map object*.

    Attributes
    ----------
    value: float
        the actual measurement
    tpoint: int
        time point index
    feature: tmlib.models.Feature
        parent feature to which the feature belongs
    mapobject_id: int
        ID of the parent mapobject
    mapobject: tmlib.models.MapobjectType
        parent mapobject to which the feature belongs
    '''

    #: Name of the corresponding database table
    __tablename__ = 'feature_values'

    #: Table columns
    value = Column(Float(precision=15))
    tpoint = Column(Integer)
    feature_id = Column(Integer, ForeignKey('features.id'))
    mapobject_id = Column(Integer, ForeignKey('mapobjects.id'))

    #: Relationships to other tables
    feature = relationship('Feature', backref='feature_values')
    mapobject = relationship('Mapobject', backref='feature_values')

    def __init__(self, value, tpoint, feature, mapobject):
        '''
        Parameters
        ----------
        value: float
            the actual measurement
        tpoint: int
            time point index
        feature: tmlib.models.Feature
            parent feature to which the feature belongs
        mapobject: tmlib.models.MapobjectType
            parent map object to which the feature belongs
        '''
        self.value = value
        self.tpoint = tpoint
        self.feature_id = feature.id
        self.mapobject_id = mapobject.id
