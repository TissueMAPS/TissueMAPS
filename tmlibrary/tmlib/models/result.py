# TmLibrary - TissueMAPS library for distibuted image analysis routines.
# Copyright (C) 2016-2018 University of Zurich.
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
from cStringIO import StringIO
import csv
import numpy as np
import pandas as pd
from sqlalchemy import (
    Integer, BigInteger, Column, String, ForeignKey, UniqueConstraint,
    PrimaryKeyConstraint, ForeignKeyConstraint
)
from sqlalchemy.dialects.postgresql import HSTORE, JSON
from sqlalchemy.orm import relationship, backref, Session

from tmlib.models.base import ExperimentModel, IdMixIn
from tmlib.models.feature import FeatureValues

logger = logging.getLogger(__name__)


class ToolResult(ExperimentModel, IdMixIn):

    '''A tool result bundles all elements that should be visualized together
    client side.
    Attributes
    ----------
    layer: tmlib.tools.layer.ToolResultLayer
        client-side map representation of a tool result
    plots: List[tmlib.tools.result.Plot]
        all plots linked to the label `layer`
    '''

    __tablename__ = 'tool_results'

    __table_args__ = (UniqueConstraint('name', 'mapobject_type_id'), )

    #: str: name of the result given by the user
    name = Column(String(50), index=True)

    #: str: name of the corresponding tool
    tool_name = Column(String(30), index=True)

    #: int: ID of the corresponding job submission
    submission_id = Column(BigInteger, index=True, unique=True)

    #: str: label layer type
    type = Column(String(50))

    #: dict: mapping of tool-specific attributes
    attributes = Column(JSON)

    __mapper_args__ = {'polymorphic_on': type}

    #: int: id of the parent mapobject type
    mapobject_type_id = Column(
        Integer,
        ForeignKey('mapobject_types.id', onupdate='CASCADE', ondelete='CASCADE'),
        index=True
    )

    #: tmlib.models.mapobject.MapobjectType: parent mapobject type
    mapobject_type = relationship(
        'MapobjectType',
        backref=backref('results', cascade='all, delete-orphan')
    )

    def __init__(self, submission_id, tool_name, mapobject_type_id,
            **extra_attributes):
        '''A persisted result that can be interpreted and visualized by the
        client.

        Parameters
        ----------
        submission_id: int
            ID of the respective job
            :class:`Submission <tmlib.models.submission.Submission>`
        tool_name: str
            name of the :class:`Tool <tmlib.tools.base.Tool>` that generated
            the result
        mapobject_type_id: int
            ID of the selected
            :class:`MapobjectType <tmlib.models.mapobject.MapobjectType>`
        **extra_attributes: dict, optional
            additional tool-specific attributes that be need to be saved
        '''
        self.tool_name = tool_name
        self.submission_id = submission_id
        self.mapobject_type_id = mapobject_type_id
        if 'name' in extra_attributes:
            self.name = extra_attributes.pop('name')
        else:
            # TODO: use setter to check whether name is valid
            self.name = '%s-%d' % (tool_name, submission_id)
        if 'type' in extra_attributes:
            self.type = extra_attributes.pop('type')
        self.attributes = extra_attributes
        for attr, value in extra_attributes.iteritems():
            # Numpy arrays are not JSON serializable
            if isinstance(value, np.ndarray) or isinstance(value, pd.Series):
                self.attributes[attr] = value.tolist()

    def get_labels(self, mapobject_ids):
        '''Queries the database to retrieve the generated label values for
        the given `mapobjects`.

        Parameters
        ----------
        mapobject_ids: List[int]
            IDs of mapobjects for which labels should be retrieved

        Returns
        -------
        Dict[int, float or int]
            mapping of mapobject ID to label value
        '''
        session = Session.object_session(self)
        return dict(
            session.query(
                LabelValues.mapobject_id,
                LabelValues.values[str(self.id)]
            ).
            filter(LabelValues.mapobject_id.in_(mapobject_ids)).
            all()
        )


class ScalarToolResult(ToolResult):

    '''Tool result that assigns each
    :class:`Mapobject <tmlib.models.mapobject.Mapobject>` a discrete value.
    '''

    __mapper_args__ = {'polymorphic_identity': 'ScalarToolResult'}

    def __init__(self, submission_id, tool_name, mapobject_type_id,
            unique_labels, **extra_attributes):
        '''
        Parameters
        ----------
        submission_id: int
            ID of the respective job
            :class:`Submission <tmlib.models.submission.Submission>`
        tool_name: str
            name of the :class:`Tool <tmlib.tools.base.Tool>` that generated
            the result
        mapobject_type_id: int
            ID of the selected
            :class:`MapobjectType <tmlib.models.mapobject.MapobjectType>`
        unique_labels : List[int]
            unique label values
        **extra_attributes: dict, optional
            additional tool-specific attributes that be need to be saved
        '''
        super(ScalarToolResult, self).__init__(
            submission_id, tool_name, mapobject_type_id,
            unique_labels=unique_labels, **extra_attributes
        )


class SupervisedClassifierToolResult(ScalarToolResult):

    '''Results of a supervised classification tool, where
    classifiers have specific colors associated with class labels.
    '''

    __mapper_args__ = {'polymorphic_identity': 'SupervisedClassifierToolResult'}

    def __init__(self, submission_id, tool_name, mapobject_type_id,
            unique_labels, label_map, **extra_attributes):
        '''
        Parameters
        ----------
        submission_id: int
            ID of the respective job
            :class:`Submission <tmlib.models.submission.Submission>`
        tool_name: str
            name of the :class:`Tool <tmlib.tools.base.Tool>` that generated
            the result
        mapobject_type_id: int
            ID of the selected
            :class:`MapobjectType <tmlib.models.mapobject.MapobjectType>`
        unique_labels : List[int]
            unique label values
        label_map : dict[float, str]
            mapping of label value to color strings of format ``"#ffffff"``
        **extra_attributes: dict, optional
            additional tool-specific attributes that be need to be saved
        '''
        super(SupervisedClassifierToolResult, self).__init__(
            submission_id, tool_name, mapobject_type_id,
            label_map=label_map, unique_labels=unique_labels, **extra_attributes
        )

class SavedSelectionsToolResult(ScalarToolResult):

    '''Results of a saved selection tool
    '''

    __mapper_args__ = {'polymorphic_identity': 'SavedSelectionsToolResult'}

    def __init__(self, submission_id, tool_name, mapobject_type_id,
            unique_labels, label_map, **extra_attributes):
        '''
        Parameters
        ----------
        submission_id: int
            ID of the respective job
            :class:`Submission <tmlib.models.submission.Submission>`
        tool_name: str
            name of the :class:`Tool <tmlib.tools.base.Tool>` that generated
            the result
        mapobject_type_id: int
            ID of the selected
            :class:`MapobjectType <tmlib.models.mapobject.MapobjectType>`
        unique_labels : List[int]
            unique label values
        label_map : dict[float, str]
            mapping of label value to color strings of format ``"#ffffff"``
        **extra_attributes: dict, optional
            additional tool-specific attributes that be need to be saved
        '''
        super(SavedSelectionsToolResult, self).__init__(
            submission_id, tool_name, mapobject_type_id,
            label_map=label_map, unique_labels=unique_labels, **extra_attributes
        )

class ContinuousToolResult(ToolResult):

    '''Tool result where each
    :class:`Mapobject <tmlib.models.mapobject.Mapobject>`
    gets assigned a continuous value.
    '''

    __mapper_args__ = {'polymorphic_identity': 'ContinuousToolResult'}

    def __init__(self, submission_id, tool_name, mapobject_type_id,
            **extra_attributes):
        '''
        Parameters
        ----------
        submission_id: int
            ID of the respective job
            :class:`Submission <tmlib.models.submission.Submission>`
        tool_name: str
            name of the :class:`Tool <tmlib.tools.base.Tool>` that generated
            the result
        mapobject_type_id: int
            ID of the selected
            :class:`MapobjectType <tmlib.models.mapobject.MapobjectType>`
        **extra_attributes: dict, optional
            additional tool-specific attributes that be need to be saved

        '''
        super(ContinuousToolResult, self).__init__(
            submission_id, tool_name, mapobject_type_id, **extra_attributes
        )


class HeatmapToolResult(ContinuousToolResult):

    '''Result of the Heatmap tool, where each
    :class:`Mapobject <tmlib.models.mapobject.Mapobject>`
    gets assigned an already available feature value.
    '''

    __mapper_args__ = {'polymorphic_identity': 'HeatmapToolResult'}

    def __init__(self, submission_id, tool_name, mapobject_type_id,
            feature_id, min, max, **extra_attributes):
        '''
        Parameters
        ----------
        submission_id: int
            ID of the respective job
            :class:`Submission <tmlib.models.submission.Submission>`
        tool_name: str
            name of the :class:`Tool <tmlib.tools.base.Tool>` that generated
            the result
        mapobject_type_id: int
            ID of the selected
            :class:`MapobjectType <tmlib.models.mapobject.MapobjectType>`
        feature_id: int
            ID of the feature whose values should be used
        min: int
            minimum feature value
        max: int
            maximum feature value
        **extra_attributes: dict, optional
            additional tool-specific attributes that be need to be saved
        '''
        super(HeatmapToolResult, self).__init__(
            submission_id, tool_name, mapobject_type_id,
            feature_id=feature_id, min=min, max=max, **extra_attributes
        )

    def get_labels(self, mapobject_ids):
        '''Queries the database to retrieve the pre-computed feature values for
        the given `mapobjects`.

        Parameters
        ----------
        mapobject_ids: List[int]
            IDs of mapobjects for which feature values should be retrieved

        Returns
        -------
        Dict[int, float or int]
            mapping of mapobject ID to feature value
        '''
        session = Session.object_session(self)
        feature_id = self.attributes['feature_id']
        return dict(
            session.query(
                FeatureValues.mapobject_id,
                FeatureValues.values[str(feature_id)]
            ).
            filter(FeatureValues.mapobject_id.in_(mapobject_ids)).
            all()
        )


class LabelValues(ExperimentModel):

    '''An individual value of a
    :class:`ToolResult <tmlib.models.result.ToolResult>`
    that was computed for a given
    :class:`Mapobject <tmlib.models.mapobject.Mapobject>`.
    '''

    __tablename__ = 'label_values'

    __table_args__ = (
        PrimaryKeyConstraint('mapobject_id', 'partition_key', 'tpoint'),
        ForeignKeyConstraint(
            ['mapobject_id', 'partition_key'],
            ['mapobjects.id', 'mapobjects.partition_key'],
            ondelete='CASCADE'
        )
    )

    __distribution_method__ = 'hash'

    __distribute_by__ = 'partition_key'

    __colocate_with__ = 'mapobjects'

    partition_key = Column(Integer, nullable=False)

    #: Dict[str, str]: mapping of tool result ID to label value encoded as text
    values = Column(HSTORE)

    #: int: zero-based time point index
    tpoint = Column(Integer, nullable=False, index=True)

    #: int: ID of the parent mapobject
    mapobject_id = Column(BigInteger, index=True)

    def __init__(self, partition_key, mapobject_id, values, tpoint):
        '''
        Parameters
        ----------
        partition_key: int
            key that determines on which shard the object will be stored
        mapobject_id: int
            ID of the mapobject to which values should be assigned
        values: Dict[str, float]
            mapping of tool result ID to value
        tpoint: int
            zero-based time point index
        '''
        self.partition_key = partition_key
        self.tpoint = tpoint
        self.values = values
        self.mapobject_id = mapobject_id

    @classmethod
    def _add(self, connection, instance):
        connection.execute('''
            INSERT INTO label_values AS v (
                partition_key, values, mapobject_id, tpoint
            )
            VALUES (
                %(partition_key)s, %(values)s, %(mapobject_id)s, %(tpoint)s
            )
            ON CONFLICT
            ON CONSTRAINT label_values_mapobject_id_tpoint_key
            DO UPDATE
            SET values = v.values || %(values)s
            WHERE v.mapobject_id = %(mapobject_id)s
            AND v.tpoint = %(tpoint)s
            AND v.partition_key = %(partition_key)s
        ''', {
            'values': instance.values,
            'mapobject_id': instance.mapobject_id,
            'tpoint': instance.tpoint
        })

    @classmethod
    def _bulk_ingest(cls, connection, instances):
        f = StringIO()
        w = csv.writer(f, delimiter=';')
        for obj in instances:
            w.writerow((
                obj.partition_key, obj.mapobject_id, obj.tpoint,
                ','.join([
                    '=>'.join([k, str(v)]) for k, v in obj.values.iteritems()
                ])
            ))
        columns = ('partition_key', 'mapobject_id', 'tpoint', 'values')
        f.seek(0)
        connection.copy_from(
            f, cls.__table__.name, sep=';', columns=columns, null=''
        )
        f.close()

    def __repr__(self):
        return (
            '<LabelValues(id=%r, tpoint=%r, mapobject_id=%r)>'
            % (self.id, self.tpoint, self.mapobject_id)
        )
