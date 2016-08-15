import logging
import numpy as np
from sqlalchemy import Integer, ForeignKey, Column, String
from sqlalchemy.orm import relationship, backref, Session
from sqlalchemy.dialects.postgresql import JSON

from tmserver.serialize import json_encoder
from tmserver.model import ExperimentModel

from tmlib.models import FeatureValue

logger = logging.getLogger(__name__)


class ToolResult(ExperimentModel):

    '''A tool result bundles all elements (label layer and plots)
    that should be visualized together client side.

    Attributes
    ----------
    name: str
        name given to the result by the user
    layer: tmserver.tool.LabelLayer
        label layer
    plots: List[tmserver.tool.Plot]
        all plots linked to the label layer
    tool_session_id: int
        ID of the respective tool session
    tool_session: tmserver.tool.ToolSession
        session for the tool request
    '''

    __tablename__ = 'tool_results'

    name = Column(String)

    tool_session_id = Column(
        Integer,
        ForeignKey('tool_sessions.id', onupdate='CASCADE', ondelete='CASCADE'),
        index=True
    )

    tool_session = relationship(
        'ToolSession',
        backref=backref('tool_sessions', cascade='all, delete-orphan')
    )

    def __init__(self, tool_session, layer, name=None, plots=[]):
        '''A persisted result object that can be interpreted and visualized by the
        client.

        Parameters
        ----------
        tool_session : tmaps.tool.ToolSession
            tool session to which this result is linked
        layer : tmaps.tool.LabelLayer
            the object that represents the client-side representation of a
            tool result on the map
        name : str, optional
            a descriptive name for this result
        plots : List[tmaps.tool.Plot], optional
            additional plots that should be visualized client-side

        '''
        session = Session.object_session(self)
        if name is None:
            self.name = '%s result' % tool_session.tool.name
        else:
            self.name = name
        self.tool_session_id = tool_session.id
        logger.info('create persistent result for tool "%s"', self.name)
        session.add(self)
        session.flush()

        # Add layer
        layer.result_id = self.id
        session.add(layer)

        # Add plots
        for plot in plots:
            plot.result_id = self.id

        session.add_all(plots)


@json_encoder(ToolResult)
def encode_result(obj, encoder):
    return {
        'id': obj.hash,
        'name': obj.name,
        'layer': obj.layer,
        'plots': map(encoder.default, obj.plots)
    }


class LabelLayer(ExperimentModel):

    '''A layer that associates each :py:class:etmlib.models.Mapobject`
    with a :py:class:`tmserver.tool.LabelLayerValue` for multi-resolution
    visualization of tool results on the map.
    The layer can be rendered client side as vector graphics and mapobjects
    can be color-coded according their respective label.

    Attributes
    ----------
    type: str
        label layer type (name of the class)
    attributes: dict
        mapping of tool-specific attributes
    mapobject_type_id: int
        ID of the parent mapobject
    mapobject_type: tmlib.models.MapobjectType
        parent mapobject type
    result_id: int
        ID of the parent result
    result: tmserver.tool.ToolResult
        parent result
    '''

    __tablename__ = 'label_layers'

    type = Column(String, index=True)
    attributes = Column(JSON)

    mapobject_type_id = Column(
        Integer,
        ForeignKey('mapobject_types.id', onupdate='CASCADE', ondelete='CASCADE'),
        index=True
    )

    mapobject_type = relationship(
        'MapobjectType',
        backref=backref('label_layers', cascade='all, delete-orphan')
    )

    result_id = Column(
        Integer,
        ForeignKey('tool_results.id', onupdate='CASCADE', ondelete='CASCADE'),
        index=True
    )

    result = relationship(
        'ToolResult',
        backref=backref('layer', cascade='all, delete-orphan', uselist=False)
    )

    def __init__(self, mapobject_type_id, labels, **extra_attributes):
        '''
        Parameters
        ----------
        mapobject_type_id: int
            ID of the parent mapobject type
        labels : dict[number, dict], optional
            mapping of mapobject ID to label value
        extra_attributes : dict, optional
            additional tool-specific attributes that be need to be saved

        '''
        session = Session.object_session(self)
        self.type = self.__class__.__name__
        self.attributes = extra_attributes
        self.mapobject_type_id = mapobject_type_id

        session.add(self)
        session.flush()

        if labels:
            logger.info('create label layer labels')
            label_objs = [
                {'mapobject_id': mapobject_id,
                 'label': label,
                 'label_layer_id': self.id}
                for mapobject_id, label in labels.items()
            ]
            session.bulk_insert_mappings(LabelLayerValue, label_objs)

    def get_labels_for_objects(self, mapobject_ids):
        '''Selects the label values for the given `mapobjects` from the database
        table.

        Parameters
        ----------
        mapobject_ids: List[int]
            IDs of selected mapobjects

        Returns
        -------
        Dict[int, float or int]
            mapping of mapobject ID to label value

        Note
        ----
        In case of the "Heatmap" tool where labels represent already computed
        feature values, the values are directly selected from the
        "feature_values" table and not stored in table "label_layer_values" to
        avoid duplication of data.

        '''
        logger.info('get labels from database table')
        session = Session.object_session(self)
        if self.type == 'HeatmapLabelLayer':
            print self.attributes['feature_id']
            return dict(
                session.query(
                    FeatureValue.mapobject_id, FeatureValue.value
                ).
                filter(
                    FeatureValue.mapobject_id.in_(mapobject_ids),
                    FeatureValue.feature_id == self.attributes['feature_id']
                ).
                all()
            )
        else:
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


@json_encoder(LabelLayer)
def encode_label_layer(obj, encoder):
    return {
        'id': obj.hash,
        'name': 'TODO:NAME',
        'type': obj.type,
        'attributes': obj.attributes
    }


class ScalarLabelLayer(LabelLayer):

    '''A label layer that assigns each mapobject a discrete value.'''

    def __init__(self, mapobject_type_id, labels, **extra_attributes):
        '''
        Parameters
        ----------
        labels : dict[number, int | float | str]
            mapping of mapobject ID to label value
        **extra_attributes : dict
            additional tool-specific attributes that need to be saved

        '''
        extra_attributes.update({'unique_labels': list(set(labels.values()))})
        super(ScalarLabelLayer, self).__init__(
            mapobject_type_id, labels, extra_attributes=extra_attributes
        )


class SupervisedClassifierLabelLayer(ScalarLabelLayer):

    '''A label layer for results of a supervised classifier.
    Results of such classifiers have specific colors associated with class
    labels.
    '''
    def __init__(self, mapobject_type_id, labels, color_map):
        '''
        Parameters
        ----------
        mapobject_type_id: int
            ID of the parent mapobject type
        labels : dict[number, int | float | str]
            mapping of mapobject ID to label value
        color_map : dict[int | float | str, str]
            mapping of label value to color strings of the format "#ffffff"
        '''
        super(SupervisedClassifierLabelLayer, self).__init__(
            mapobject_type_id, labels, color_map=color_map
        )


class ContinuousLabelLayer(LabelLayer):

    '''A label layer where each mapobject gets assigned a continuous value.'''

    def __init__(self, mapobject_type_id, labels):
        '''
        Parameters
        ---------
        mapobject_type_id: int
            ID of the parent mapobject type
        labels : dict[number, float]
            mapping of mapobject ID to label value

        '''
        super(ContinuousLabelLayer, self).__init__(
            mapobject_type_id, labels
        )


class HeatmapLabelLayer(LabelLayer):

    '''A label layer where each mapobject gets assigned an already available
    feature value.
    '''

    def __init__(self, mapobject_type_id, feature_id):
        '''
        Parameters
        ----------
        mapobject_type_id: int
            ID of the parent mapobject type
        feature_id: int
            ID of the feature whose values should be used

        '''
        if not 'feature_id' in extra_attributes:
            raise ValueError(
                'Argument "extra_attributes" of heatmap tool must be a mapping '
                'that specifies "feature_id".'
            )
        labels = {}
        super(HeatmapLabelLayer, self).__init__(
            mapobject_type_id, labels, feature_id=feature_id
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
    label_layer: tmserver.tool.LabelLayer
        parent label layer
    '''

    __tablename__ = 'label_layer_values'

    __distribute_by_hash__ = 'mapobject_id'

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
    laber_layer = relationship(
        'LabelLayer',
        backref=backref('labels', cascade='all, delete-orphan')
    )
    mapobject = relationship(
        'Mapobject',
        backref=backref('labels', cascade='all, delete-orphan')
    )

    def __init__(self, label_layer_id, mapobject_id):
        '''
        Parameters
        ----------
        label_layer_id: int
            ID of the parent label layer
        mapobject_id: int
            ID of the mapobject to which the value is assigned
        '''
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
    result: tmserver.tool.Result
        parent result
    '''

    __tablename__ = 'plots'

    type = Column(String, index=True)
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

    def __init__(self, attributes):
        '''
        Parameters
        ---------
        attributes : dict
            mapping that's interpreted by the client tool handler

        '''
        self.type == self.__class__.__name__
        self.attributes = attributes
        # result_id ???


@json_encoder(Plot)
def encode_plot(obj, encoder):
    return {
        'id': obj.hash,
        'type': obj.type,
        'attributes': obj.attributes
    }
