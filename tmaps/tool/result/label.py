from sqlalchemy import Integer, ForeignKey, Column, Float
from sqlalchemy.orm import relationship

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

        session.add(self)
        session.flush()

        label_objs = []
        ids = Mapobject.translate_external_ids(
            ids, session.experiment_id, mapobject_type.id)
        for ext_id, label in zip(ids, labels):
            pl = LabelResultLabel(
                mapobject_id=ext_id, label=label,
                label_result_id=self.id)
            label_objs.append(pl)

        session.add_all(label_objs)
        session.commit()

    def to_dict(self):
        return {
            'id': self.id
        }

    def get_labels_for_objects(self, mapobject_ids):
        return dict(
            [(l.mapobject_id, l.label)
             for l in self.labels
             if l.mapobject_id in set(mapobject_ids)])


class LabelResultLabel(Model):
    __tablename__ = 'label_result_labels'

    mapobject_id = Column(
        Integer, ForeignKey('mapobjects.id'))
    label_result_id = \
        Column(Integer, ForeignKey('label_results.id'))

    label_result = relationship('LabelResult', backref='labels')
    mapobject = relationship('Mapobject', backref='labels')
    label = Column(Float(precision=15))
