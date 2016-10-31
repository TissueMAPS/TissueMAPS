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
import numpy as np
from cached_property import cached_property
from abc import abstractmethod
from abc import abstractproperty
from sqlalchemy import Integer, ForeignKey, Column, String
from sqlalchemy.orm import relationship, backref, Session
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.ext.declarative import declared_attr

from tmlib.models import ExperimentModel
from tmlib.models import FeatureValue

logger = logging.getLogger(__name__)


class ToolResult(ExperimentModel):

    '''A tool result bundles all elements (label layer and plots)
    that should be visualized together client side.

    Attributes
    ----------
    name: str
        name given to the result by the user
    layer: tmlib.tools.result.LabelLayer
        the object that represents the client-side representation of a
        tool result on the map
    plots: List[tmlib.tools.result.Plot]
        all plots linked to the label layer
    submission_id: int
        ID of the respective job submission
    '''

    __tablename__ = 'tool_results'

    name = Column(String(50), index=True)
    tool_name = Column(String(30), index=True)
    submission_id = Column(Integer, index=True)

    def __init__(self, submission_id, tool_name, name=None):
        '''A persisted result that can be interpreted and visualized by the
        client.

        Parameters
        ----------
        submission_id: int
            ID of the respective job submission
        tool_name: str
            name of the tool that generated the result
        name: str, optional
            a descriptive name for this result
        '''
        if name is None:
            self.name = '%s-%d result' % (tool_name, submission_id)
        else:
            self.name = name
        self.tool_name = tool_name
        self.submission_id = submission_id


class LabelLayer(ExperimentModel):

    '''A layer that associates each :class:etmlib.models.Mapobject`
    with a :class:`tmlib.tools.result.LabelLayerValue` for multi-resolution
    visualization of tool results on the map.
    The layer can be rendered client side as vector graphics and mapobjects
    can be color-coded according their respective label.

    Attributes
    ----------
    type: str
        label layer type (name of the derived class)
    attributes: dict
        mapping of tool-specific attributes
    mapobject_type_id: int
        ID of the parent mapobject
    mapobject_type: tmlib.models.MapobjectType
        parent mapobject typeresult_id: int
        ID of the parent result
    result: tmlib.tools.result.ToolResult
        parent result
    '''

    __tablename__ = 'label_layers'

    type = Column(String(50))
    attributes = Column(JSON)

    __mapper_args__ = {'polymorphic_on': type}

    # __table_args__ = {'extend_existing': True}

    mapobject_type_id = Column(
        Integer,
        ForeignKey('mapobject_types.id', onupdate='CASCADE', ondelete='CASCADE'),
        index=True
    )
    tool_result_id = Column(
        Integer,
        ForeignKey('tool_results.id', onupdate='CASCADE', ondelete='CASCADE'),
        index=True
    )

    mapobject_type = relationship(
        'MapobjectType',
        backref=backref('label_layers', cascade='all, delete-orphan')
    )
    tool_result = relationship(
        'ToolResult',
        backref=backref('layer', cascade='all, delete-orphan', uselist=False)
    )

    def __init__(self, tool_result_id, mapobject_type_id, **extra_attributes):
        '''
        Parameters
        ----------
        tool_result_id: int
            ID of the parent tool result
        mapobject_type_id: int
            ID of the corresponding :class:`tmlib.models.MapobjectType`
        **extra_attributes: dict, optional
            additional tool-specific attributes that be need to be saved
        '''
        self.tool_result_id = tool_result_id
        self.mapobject_type_id = mapobject_type_id
        labels = extra_attributes.pop('labels', None)
        self.attributes = extra_attributes

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
                LabelLayerValue.mapobject_id, LabelLayerValue.label
            ).
            filter(
                LabelLayerValue.mapobject_id.in_(mapobject_ids),
                LabelLayerValue.label_layer_id == self.id
            ).
            all()
        )


class ScalarLabelLayer(LabelLayer):

    '''A label layer that assigns each mapobject a discrete value.'''

    __mapper_args__ = {'polymorphic_identity': 'ScalarLabelLayer'}

    def __init__(self, tool_result_id, mapobject_type_id, unique_labels,
            **extra_attributes):
        '''
        Parameters
        ----------
        tool_result_id: int
            ID of the parent tool result
        mapobject_type_id: int
            ID of the corresponding :class:`tmlib.models.MapobjectType`
        unique_labels : List[int]
            unique label values
        **extra_attributes: dict, optional
            additional tool-specific attributes that be need to be saved
        '''
        super(ScalarLabelLayer, self).__init__(
            tool_result_id, mapobject_type_id, unique_labels=unique_labels,
            **extra_attributes
        )


class SupervisedClassifierLabelLayer(ScalarLabelLayer):

    '''A label layer for results of a supervised classifier.
    Results of such classifiers have specific colors associated with class
    labels.
    '''

    __mapper_args__ = {'polymorphic_identity': 'SupervisedClassifierLabelLayer'}

    def __init__(self, tool_result_id, mapobject_type_id, unqiue_labels,
            color_map, **extra_attributes):
        '''
        Parameters
        ----------
        tool_result_id: int
            ID of the parent tool result
        mapobject_type_id: int
            ID of the corresponding :class:`tmlib.models.MapobjectType`
        unique_labels : List[int]
            unique label values
        color_map : dict[int | float | str, str]
            mapping of label value to color strings of the format "#ffffff"
        **extra_attributes: dict, optional
            additional tool-specific attributes that be need to be saved
        '''
        super(SupervisedClassifierLabelLayer, self).__init__(
            tool_result_id, mapobject_type_id, color_map=color_map,
            unique_labels=unique_labels, **extra_attributes
        )


class ContinuousLabelLayer(LabelLayer):

    '''A label layer where each mapobject gets assigned a continuous value.'''

    __mapper_args__ = {'polymorphic_identity': 'ContinuousLabelLayer'}

    def __init__(self, tool_result_id, mapobject_type_id, **extra_attributes):
        '''
        Parameters
        ---------
        tool_result_id: int
            ID of the parent tool result
        mapobject_type_id: int
            ID of the corresponding :class:`tmlib.models.MapobjectType`
        **extra_attributes: dict, optional
            additional tool-specific attributes that be need to be saved

        '''
        super(ContinuousLabelLayer, self).__init__(
            tool_result_id, mapobject_type_id, **extra_attributes
        )


class HeatmapLabelLayer(ContinuousLabelLayer):

    '''A label layer for results of the Heatmap tool, where each mapobject
    gets assigned an already available feature value.
    '''

    __mapper_args__ = {'polymorphic_identity': 'HeatmapLabelLayer'}

    def __init__(self, tool_result_id, mapobject_type_id, feature_id, min, max):
        '''
        Parameters
        ----------
        tool_result_id: int
            ID of the parent tool result
        mapobject_type_id: int
            ID of the parent mapobject type
        feature_id: int
            ID of the feature whose values should be used
        '''
        super(HeatmapLabelLayer, self).__init__(
            tool_result_id, mapobject_type_id, feature_id=feature_id,
            min=min, max=max
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
        layer = session.query(self.__class__).\
            filter_by(session_id=self.session_id).\
            one()
        return dict(
            session.query(
                FeatureValue.mapobject_id, FeatureValue.value
            ).
            filter(
                FeatureValue.mapobject_id.in_(mapobject_ids),
                FeatureValue.feature_id == layer.attributes['feature_id']
            ).
            all()
        )


class LabelLayerValue(ExperimentModel):

    '''A label that's assigned to an indiviual mapobject.

    Attributes
    ----------
    label: dict
        label value
    mapobject_id: int
        ID of the parent mapobject
    mapobject: tmlib.models.Mapobject
        parent mapobject
    label_layer_id: int
        ID of the parent label layer
    label_layer: tmlib.tools.result.LabelLayer
        parent label layer
    '''

    __tablename__ = 'label_layer_values'

    label = Column(JSON)
    mapobject_id = Column(
        Integer,
        ForeignKey('mapobjects.id', onupdate='CASCADE', ondelete='CASCADE'),
        index=True
    )
    label_layer_id = Column(
        Integer,
        ForeignKey('label_layers.id', onupdate='CASCADE', ondelete='CASCADE'),
        index=True
    )

    # TODO: does this mapping work with subclasses of LabelLayer?
    # label_layer = relationship(
    #     'LabelLayer',
    #     backref=backref('labels', cascade='all, delete-orphan')
    # )
    mapobject = relationship(
        'Mapobject',
        backref=backref('labels', cascade='all, delete-orphan')
    )

    def __init__(self, label, label_layer_id, mapobject_id):
        '''
        Parameters
        ----------
        label:
            label value
        label_layer_id: int
            ID of the parent label layer
        mapobject_id: int
            ID of the mapobject to which the value is assigned
        '''
        self.label = label
        self.label_layer_id = label_layer_id
        self.mapobject_id = mapobject_id


class Plot(ExperimentModel):

    '''A plot that can be visualized client side along with a label layer.

    Attributes
    ----------
    type: str
        plot type (name of the class)
    attributes: dict
        mapping that's interpreted by the client tool handler
    result_id: int
        ID of the parent result
    result: tmlib.tools.result.Result
        parent result
    '''

    __tablename__ = 'plots'

    attributes = Column(JSON)
    result_id = Column(
        Integer,
        ForeignKey('tool_results.id', onupdate='CASCADE', ondelete='CASCADE'),
        index=True
    )
    result = relationship(
        'ToolResult',
        backref=backref('plots', cascade='all, delete-orphan')
    )

    def __init__(self, attributes, result_id):
        '''
        Parameters
        ---------
        attributes: dict
            mapping that's interpreted by the client tool handler
        result_id: int
            ID of the parent tool result

        '''
        self.attributes = attributes
        self.result_id = result_id


