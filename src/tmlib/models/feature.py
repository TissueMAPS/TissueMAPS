import logging
from sqlalchemy import Column, String, Integer, Float, ForeignKey, Boolean
from sqlalchemy.orm import relationship, backref
from sqlalchemy import UniqueConstraint

from tmlib.models.base import Model

logger = logging.getLogger(__name__)


class Feature(Model):

    '''A *feature* is a measurement that is associated with a particular
    *map object type*. For example a *feature* named "Morphology_Area"
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
    values: List[tmlib.models.FeatureValues]
        values that belong to the feature
    '''

    #: str: name of the corresponding database table
    __tablename__ = 'features'

    __table_args__ = (UniqueConstraint('name', 'mapobject_type_id'), )

    # Table columns
    name = Column(String, index=True)
    is_aggregate = Column(Boolean, index=True)
    mapobject_type_id = Column(
        Integer,
        ForeignKey('mapobject_types.id', onupdate='CASCADE', ondelete='CASCADE'),
        index=True
    )

    # Relationships to other tables
    mapobject_type = relationship(
        'MapobjectType',
        backref=backref('features', cascade='all, delete-orphan')
    )

    def __init__(self, name, mapobject_type_id, is_aggregate=False):
        '''
        Parameters
        ----------
        name: str
            name of the feature
        mapobject_type_id: int
            ID of parent mapobject type
        is_aggregate: bool, optional
            whether the feature is an aggregate calculated based on another
            feature
        '''
        self.name = name
        self.mapobject_type_id = mapobject_type_id
        self.is_aggregate = is_aggregate

    def __repr__(self):
        return '<Feature(id=%r, name=%r)>' % (self.id, self.name)


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

    #: str: name of the corresponding database table
    __tablename__ = 'feature_values'

    __table_args__ = (
        UniqueConstraint('tpoint', 'feature_id', 'mapobject_id'),
    )

    # Table columns
    value = Column(Float(precision=15))
    tpoint = Column(Integer, index=True)
    feature_id = Column(
        Integer,
        ForeignKey('features.id', onupdate='CASCADE', ondelete='CASCADE'),
        index=True
    )
    mapobject_id = Column(
        Integer,
        ForeignKey('mapobjects.id', onupdate='CASCADE', ondelete='CASCADE')
    )

    # Relationships to other tables
    feature = relationship(
        'Feature',
        backref=backref('values', cascade='all, delete-orphan')
    )
    mapobject = relationship(
        'Mapobject',
        backref=backref('feature_values', cascade='all, delete-orphan')
    )

    def __init__(self, feature_id, mapobject_id, value=None, tpoint=None):
        '''
        Parameters
        ----------
        feature: tmlib.models.Feature
            parent feature to which the feature belongs
        mapobject_id: int
            ID of the parent mapobject
        value: float, optional
            the actual measurement (default: ``None``)
        tpoint: int, optional
            time point index (default: ``None``)
        '''
        self.tpoint = tpoint
        self.feature_id = feature_id
        self.mapobject_id = mapobject_id
        self.value = value

    def __repr__(self):
        return (
            '<FeatureValue(id=%d, tpoint=%d, mapobject=%r, feature=%r)>'
            % (self.id, self.tpoint, self.mapobject_id, self.feature.name)
        )
