from sqlalchemy import Integer, ForeignKey, Column, Float
from sqlalchemy.orm import relationship

from tmaps.serialize import json_encoder
from tmaps.extensions import db
from tmaps.model import Model
from tmaps.mapobject import Mapobject


class LabelResult(Model):
    __tablename__ = 'label_results'

    tool_session_id = \
        Column(Integer, ForeignKey('tool_sessions.id'))
    mapobject_type_id = Column(
        Integer, ForeignKey('mapobject_types.id'))
    mapobject_type = relationship(
        'MapobjectType', backref='label_results')

    def __init__(self, ids, labels, mapobject_type, session):
        self.mapobject_type_id = mapobject_type.id
        self.tool_session_id = session.id

        db.session.add(self)
        db.session.flush()

        label_objs = []
        for mapobject_id, label in zip(ids, labels):
            pl = LabelResultLabel(
                mapobject_id=mapobject_id, label=label,
                label_result_id=self.id)
            label_objs.append(pl)

        db.session.add_all(label_objs)
        db.session.commit()

    def get_labels_for_objects(self, mapobject_ids):
        return dict(
            [(l.mapobject_id, l.label)
             for l in self.labels
             if l.mapobject_id in set(mapobject_ids)])


@json_encoder(LabelResult)
def encode_tool(obj, encoder):
    return {
        'id': obj.hash,
    }


class LabelResultLabel(Model):
    __tablename__ = 'label_result_labels'

    mapobject_id = Column(
        Integer, ForeignKey('mapobjects.id'))
    label_result_id = \
        Column(Integer, ForeignKey('label_results.id'))

    label_result = relationship('LabelResult', backref='labels')
    mapobject = relationship('Mapobject', backref='labels')
    label = Column(Float(precision=15))


