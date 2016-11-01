# TmLibrary - TissueMAPS library for distibuted image analysis routines.
# Copyright (C) 2016  Markus D. Herrmann, University of Zurich and Robin Hafen
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
import logging
from sqlalchemy import Column, String, Integer, Float, ForeignKey, Boolean
from sqlalchemy.orm import relationship, backref
from sqlalchemy import UniqueConstraint

from tmlib.models import ExperimentModel

logger = logging.getLogger(__name__)


class Feature(ExperimentModel):

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

    __tablename__ = 'features'

    __table_args__ = (UniqueConstraint('name', 'mapobject_type_id'), )

    #: str: name given to the feature (e.g. by jterator)
    name = Column(String, index=True)

    #: bool: whether the feature is an aggregate of child object features
    is_aggregate = Column(Boolean, index=True)

    #: int: ID of parent mapobject type
    mapobject_type_id = Column(
        Integer,
        ForeignKey('mapobject_types.id', onupdate='CASCADE', ondelete='CASCADE'),
        index=True
    )

    #: tmlib.models.mapobject.MapobjectType: parent mapobject type
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


class FeatureValue(ExperimentModel):

    '''An individual value of a *feature* that was measured for a given
    *map object*.

    '''

    __tablename__ = 'feature_values'

    __table_args__ = (
        UniqueConstraint('tpoint', 'feature_id', 'mapobject_id'),
    )

    __distribute_by_hash__ = 'mapobject_id'

    #: float: the actual extracted feature value
    value = Column(Float(precision=15))

    #: int: zero-based time point index
    tpoint = Column(Integer, index=True)

    #: int: ID of the parent feature
    feature_id = Column(
        Integer,
        ForeignKey('features.id', onupdate='CASCADE', ondelete='CASCADE'),
        index=True
    )

    #: int: ID of the parent mapobject
    mapobject_id = Column(
        Integer,
        ForeignKey('mapobjects.id', onupdate='CASCADE', ondelete='CASCADE'),
        index=True
    )

    #: tmlib.models.feature.Feature: parent feature
    feature = relationship(
        'Feature',
        backref=backref('values', cascade='all, delete-orphan')
    )

    #: tmlib.models.mapobject.Mapobject: parent mapobject
    #: for which the feature was extracted
    mapobject = relationship(
        'Mapobject',
        backref=backref('feature_values', cascade='all, delete-orphan')
    )

    def __init__(self, feature_id, mapobject_id, value=None, tpoint=None):
        '''
        Parameters
        ----------
        feature_id: int
            ID of parent feature
        mapobject_id: int
            ID of parent mapobject
        value: float, optional
            actual measurement (default: ``None``)
        tpoint: int, optional
            zero-based time point index (default: ``None``)
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

