import logging
import numpy as np
from sqlalchemy import Integer, ForeignKey, Column, String
from sqlalchemy.orm import relationship, backref
from sqlalchemy.dialects.postgresql import JSON

from tmaps.serialize import json_encoder
from tmaps.model import Model
from tmaps.extensions import db

logger = logging.getLogger(__name__)


class Result(Model):
    __tablename__ = 'results'

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
        """A persisted result object that can be interpreted and visualized by the
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

        """
        if name is None:
            self.name = '%s result' % tool_session.tool.name
        else:
            self.name = name
        self.tool_session_id = tool_session.id
        logger.info('create persistent result for tool "%s"', self.name)
        db.session.add(self)
        db.session.flush()

        # Add layer
        layer.result_id = self.id
        db.session.add(layer)

        # Add plots
        for plot in plots:
            plot.result_id = self.id

        db.session.add_all(plots)


@json_encoder(Result)
def encode_result(obj, encoder):
    return {
        'id': obj.hash,
        'name': obj.name,
        'layer': obj.layer,
        'plots': map(encoder.default, obj.plots)
    }


class LabelLayer(Model):
    __tablename__ = 'label_layers'

    type = Column(String, index=True)
    attributes = Column(JSON)
    result_id = Column(
        Integer,
        ForeignKey('results.id', onupdate='CASCADE', ondelete='CASCADE'),
        index=True
    )

    result = relationship(
        'Result',
        backref=backref('layer', cascade='all, delete-orphan', uselist=False)
    )

    def __init__(self, labels, extra_attributes={}):
        """A layer that associates with each mapobject a certain value.

        Parameters
        ----------
        labels : dict[number, dict]
            a dictionary that maps a mapobject id to some value
        extra_attributes : dict
            a dictionary with extra attributes to be saved

        """
        self.type = self.__class__.__name__
        self.attributes = extra_attributes

        db.session.add(self)
        db.session.flush()

        logger.info('create label layer labels')
        label_objs = [
            {'mapobject_id': mapobject_id,
             'label': label,
             'label_layer_id': self.id}
            for mapobject_id, label in labels.items()
        ]
        db.session.bulk_insert_mappings(LabelLayerLabel, label_objs)

    def get_labels_for_objects(self, mapobject_ids):
        return dict([
            (l.mapobject_id, l.label)
             for l in self.labels
             if l.mapobject_id in set(mapobject_ids)
        ])


@json_encoder(LabelLayer)
def encode_label_layer(obj, encoder):
    return {
        'id': obj.hash,
        'name': 'TODO:NAME',
        'type': obj.type,
        'attributes': obj.attributes
    }


class ScalarLabelLayer(LabelLayer):
    def __init__(self, labels, extra_attributes={}):
        """A tool layer that assigns each mapobject a discrete value like a number
        of a string.

        Parameters
        ----------
        labels : dict[number, int | float | str]
            a dictionary that maps a mapobject id to some discrete value
        extra_attributes : dict
            a dictionary with extra attributes to be saved

        """
        extra_attributes.update({
            'unique_labels': list(set(labels.values()))
        })
        super(ScalarLabelLayer, self).__init__(
            labels, extra_attributes=extra_attributes
        )


class SupervisedClassifierLabelLayer(ScalarLabelLayer):
    def __init__(self, labels, color_map, extra_attributes={}):
        """A result of a supervised classifier like an SVM.
        Results of such classifiers have specific colors associated with class
        labels.

        Parameters
        ----------
        labels : dict[number, int | float | str]
            a dictionary that maps a mapobject id to some discrete value
        color_map : dict[int | float | str, str]
            a map from labels to color strings of the format '#ffffff'
        extra_attributes : dict
            a dictionary with extra attributes to be saved

        """
        extra_attributes.update({
            'color_map': color_map
        })
        super(SupervisedClassifierLabelLayer, self).__init__(
            labels, extra_attributes=extra_attributes
        )


class ContinuousLabelLayer(LabelLayer):
    def __init__(self, labels, extra_attributes={}):
        """A tool result that assigns each mapobject a (pseudo)-continuous value.
        Assigning each cell a numeric value based on its area would be an
        example for such a layer.

        Parameters
        ---------
        labels : dict[number, float]
            a dictionary that maps a mapobject id to some continuous value
        extra_attributes : dict
            a dictionary with extra attributes to be saved

        """
        extra_attributes.update({
            'min': np.min(labels.values()),
            'max': np.max(labels.values())
        })
        super(ContinuousLabelLayer, self).__init__(
            labels, extra_attributes=extra_attributes
        )


class LabelLayerLabel(Model):
    __tablename__ = 'label_layer_labels'

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


class Plot(Model):
    __tablename__ = 'plots'

    type = Column(String, index=True)
    attributes = Column(JSON)
    result_id = Column(
        Integer,
        ForeignKey('results.id', onupdate='CASCADE', ondelete='CASCADE'),
        index=True
    )
    result = relationship(
        'Result',
        backref=backref('plots', cascade='all, delete-orphan')
    )

    def __init__(self, attributes):
        """A persisted plot that belongs to a persisted tool result.

        Parameters
        ---------
        attributes : dict
            a dictionary of the plot attributes that are interpreted by the
            respective client handler

        """

        self.type == self.__class__.__name__
        self.attributes = attributes


@json_encoder(Plot)
def encode_plot(obj, encoder):
    return {
        'id': obj.hash,
        'type': obj.type,
        'attributes': obj.attributes
    }
