import os
import logging
from geoalchemy2 import Geometry
from sqlalchemy.orm import Session
from sqlalchemy import Column, String, Integer, Boolean, ForeignKey
from sqlalchemy.orm import relationship, backref
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy import UniqueConstraint

from tmlib.models.base import Model, DateMixIn
from tmlib.utils import autocreate_directory_property

logger = logging.getLogger(__name__)


class MapobjectType(Model, DateMixIn):

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
    mapobjects: List[tmlib.models.Mapobject]
        mapobjects that belong to the mapobject type
    '''

    #: str: name of the corresponding database table
    __tablename__ = 'mapobject_types'

    __table_args__ = (UniqueConstraint('name', 'experiment_id'), )

    # Table columns
    name = Column(String, index=True)
    _min_poly_zoom = Column('min_poly_zoom', Integer)
    experiment_id = Column(Integer, ForeignKey('experiments.id'))

    #: Relationship to other tables
    experiment = relationship(
        'Experiment',
        backref=backref('mapobject_types', cascade='all, delete-orphan')
    )

    def __init__(self, name, experiment_id):
        '''
        Parameters
        ----------
        name: str
            name of the map objects type, e.g. "cells"
        experiment_id: int
            ID of the parent experiment
        '''
        self.name = name
        self.experiment_id = experiment_id

    @autocreate_directory_property
    def location(self):
        '''str: location where data related to the mapobject type is stored'''
        return os.path.join(self.experiment.mapobject_types_location, self.name)

    @hybrid_property
    def min_poly_zoom(self):
        '''int: zoom level at which visualization switches from drawing
        polygons instead of centroids
        '''
        return self._min_poly_zoom

    @min_poly_zoom.setter
    def min_poly_zoom(self, value):
        self._min_poly_zoom = value

    def get_mapobject_outlines_within_tile(self, x, y, z, tpoint, zplane):
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
        session = Session.object_session(self)

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

    def __repr__(self):
        return '<MapobjectType(id=%d, name=%r)>' % (self.id, self.name)


class Mapobject(Model):

    '''A *map object* represents a connected pixel component in an
    image. It has outlines for drawing on the map and may also be associated
    with measurements (*features*), which can be queried or used for analysis.

    Attributes
    ----------
    is_border: bool
        whether the object touches at the border of a *site* and is
        therefore only partially represented on the corresponding image
    mapobject_type_id: int
        ID of the parent mapobject
    mapobject_type: tmlib.models.MapobjectType
        parent mapobject type to which the mapobject belongs
    site_id: int
        ID of the parent site
    site: tmlib.models.Site
        parent site to which the mapobject belongs
    outlines: List[tmlib.models.MapobjectOutlines]
        outlines that belong to the mapobject
    feature_values: List[tmlib.models.FeatureValues]
        feature values that belong to the mapobject
    '''

    #: str: name of the corresponding database table
    __tablename__ = 'mapobjects'

    __table_args__ = (
        UniqueConstraint('label', 'site_id', 'mapobject_type_id'),
    )

    # Table columns
    label = Column(Integer, index=True)
    is_border = Column(Boolean, index=True)
    site_id = Column(Integer, ForeignKey('sites.id'))
    mapobject_type_id = Column(Integer, ForeignKey('mapobject_types.id'))

    # TODO: monkey-patch additional columns for MapObject "attributes"

    # Relationships to other tables
    site = relationship('Site', backref='sites')
    mapobject_type = relationship(
        'MapobjectType',
        backref=backref('mapobjects', cascade='all, delete-orphan')
    )

    def __init__(self, label, site_id, mapobject_type_id):
        '''
        Parameters
        ----------
        label: int
            mapobject label (site-specific ID)
        site_id: int
            ID of the parent site
        mapobject_type_id: int
            ID of the parent mapobject
        '''
        self.label = label
        self.site_id = site_id
        self.mapobject_type_id = mapobject_type_id

    def __repr__(self):
        return '<Mapobject(id=%d)>' % self.id


class MapobjectOutline(Model):

    '''Outline of an individual *map object*.

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

    #: str: name of the corresponding database table
    __tablename__ = 'mapobject_outlines'

    __table_args__ = (UniqueConstraint('tpoint', 'zplane', 'mapobject_id'), )

    # Table columns
    tpoint = Column(Integer, index=True)
    zplane = Column(Integer, index=True)
    geom_poly = Column(Geometry('POLYGON'))
    geom_centroid = Column(Geometry('POINT'))
    mapobject_id = Column(Integer, ForeignKey('mapobjects.id'))

    # Relationships to other tables
    mapobject = relationship(
        'Mapobject',
        backref=backref('outlines', cascade='all, delete-orphan')
    )

    def __init__(self, tpoint, zplane, mapobject_id, geom_poly=None,
                 geom_centroid=None):
        '''
        Parameters
        ----------
        tpoint: int
            time point index
        zplane: int
            z-plane index
        mapobject_id: int
            ID of parent mapobject
        geom_poly: str, optional
            EWKT polygon geometry (default: ``None``)
        geom_centroid: str, optional
            EWKT point geometry (default: ``None``)
        '''
        self.tpoint = tpoint
        self.zplane = zplane
        self.mapobject_id = mapobject_id
        self.geom_poly = geom_poly
        self.geom_centroid = geom_centroid

    @staticmethod
    def intersection_filter(x, y, z):
        '''Generates an `SQLalchemy` query filter to select mapobject outlines
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

        tile = 'POLYGON(({maxx} {maxy}, {minx} {maxy}, {minx} {miny}, {maxx} {miny}, {maxx} {maxy}))'.format(
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
