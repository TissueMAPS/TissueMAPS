import numpy as np
from sqlalchemy import Integer, ForeignKey, Column, String
from sqlalchemy.orm import relationship, backref
from sqlalchemy.dialects.postgresql import JSON

from tmaps.serialize import json_encoder
from tmaps.model import Model
from tmaps.extensions import db


class Result(Model):
    __tablename__ = 'results'

    tool_session_id = Column(
        Integer,
        ForeignKey('tool_sessions.id', onupdate='CASCADE', ondelete='CASCADE')
    )
    mapobject_type_id = Column(
        Integer,
        ForeignKey(
            'mapobject_types.id', onupdate='CASCADE', ondelete='CASCADE')
    )
    tool_session = relationship(
        'ToolSession',
        backref=backref('tool_sessions', cascade='all, delete-orphan')
    )
    mapobject_type = relationship(
        'MapobjectType',
        backref=backref('label_results', cascade='all, delete-orphan')
    )

    def __init__(self, tool_session, layer, plots=[]):
        """A persisted result object that can be interpreted and visualized by the
        client.

        Parameters
        ----------
        tool_session : tmaps.tool.ToolSession
            tool session to which this result is linked
        layer : tmaps.tool.LabelLayer
            the object that represents the client-side representation of a
            tool result on the map
        plots : List[tmaps.tool.Plot], optional
            additional plots that should be visualized client-side

        """
        self.tool_session_id = tool_session.id

        db.session.add(self)
        db.session.flush()

        # Add layer
        layer.result_id = self.id
        db.session.flush(layer)

        # Add plots
        for plot in plots:
            plot.result_id = self.id
            db.session.flush(plot)

        db.session.commit()


@json_encoder(Result)
def encode_result(obj, encoder):
    return {
        'id': obj.hash,
        'layer': obj.layer,
        'plots': map(encoder.default, obj.plots)
    }


class LabelLayer(Model):
    __tablename__ = 'label_layers'

    type = Column(String)

    result_id = Column(
        Integer,
        ForeignKey('results.id', onupdate='CASCADE', ondelete='CASCADE')
    )
    attributes = Column(JSON)

    result = relationship(
        'Result',
        backref=backref('layer', cascade='all, delete-orphan')
    )

    result_type = Column(String)
    attributes = Column(JSON)

    def __init__(self, labels):
        """A layer that associates with each mapobject a certain value.

        Parameters
        ----------
        labels : dict[number, dict]
            a dictionary that maps a mapobject id to some value

        """

        self.type == self.__class__.__name__
        self.attributes = {}

        db.session.add(self)
        db.session.flush()

        label_objs = []
        for mapobject_id, label in labels.items():
            pl = LabelLayerLabel(
                mapobject_id=mapobject_id,
                label=label,
                label_result_id=self.id)
            label_objs.append(pl)

        db.session.add_all(label_objs)
        db.session.commit()

    def get_labels_for_objects(self, mapobject_ids):
        return dict(
            [(l.mapobject_id, l.label)
             for l in self.labels
             if l.mapobject_id in set(mapobject_ids)]
        )


@json_encoder(LabelLayer)
def encode_label_layer(obj, encoder):
    return {
        'id': obj.hash,
        'type': obj.type,
        'attributes': obj.attributes
    }


class ScalarLabelLayer(LabelLayer):
    def __init__(self, labels):
        """A tool layer that assigns each mapobject a discrete value like a number
        of a string.

        Parameters
        ----------
        labels : dict[number, int | float | str]
            a dictionary that maps a mapobject id to some discrete value

        """
        super(ScalarLabelLayer, self).__init__(labels)
        self.attributes['unique_labels'] = list(set(labels))


class SupervisedClassifierResult(ScalarLabelLayer):
    def __init__(self, labels, color_map):
        """A result of a supervised classifier like an SVM.
        Results of such classifiers have specific colors associated with class
        labels.

        Parameters
        ----------
        labels : dict[number, int | float | str]
            a dictionary that maps a mapobject id to some discrete value
        color_map : dict[int | float | str, str]
            a map from labels to color strings of the format '#ffffff'

        """
        super(SupervisedClassifierResult, self).__init__(labels)
        self.attributes['color_map'] = color_map


class ContinuousLabelLayer(LabelLayer):
    def __init__(self, labels):
        """A tool result that assigns each mapobject a (pseudo)-continuous value.
        Assigning each cell a numeric value based on its area would be an
        example for such a layer.

        Parameters
        ---------
        labels : dict[number, float]
            a dictionary that maps a mapobject id to some continuous value

        """
        super(ContinuousLabelLayer, self).__init__(labels)
        self.attributes.update({
            'min': np.min(labels),
            'max': np.max(labels)
        })


class LabelLayerLabel(Model):
    __tablename__ = 'label_layer_labels'

    label = Column(JSON)
    mapobject_id = Column(
        Integer,
        ForeignKey('mapobjects.id', onupdate='CASCADE', ondelete='CASCADE')
    )
    label_layer_id = Column(
        Integer,
        ForeignKey('label_layers.id', onupdate='CASCADE', ondelete='CASCADE')
    )
    laber_layer = relationship(
        'LabelLayer',
        backref=backref('layer', cascade='all, delete-orphan')
    )
    mapobject = relationship(
        'Mapobject',
        backref=backref('labels', cascade='all, delete-orphan')
    )


class Plot(Model):
    __tablename__ = 'plots'

    type = Column(String)
    result_id = Column(
        Integer,
        ForeignKey('results.id', onupdate='CASCADE', ondelete='CASCADE')
    )
    result = relationship(
        'Result',
        backref=backref('plots', cascade='all, delete-orphan')
    )
    attributes = Column(JSON)

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
