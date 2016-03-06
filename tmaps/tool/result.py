from tmaps.extensions.database import db
from tmaps.model import CRUDMixin, Model
from tmaps.mapobject import Mapobject


class ClassificationResult(Model, CRUDMixin):
    __tablename__ = 'classification_result'
    id = db.Column(db.Integer, primary_key=True)
    mapobject_name = db.Column(db.String(120))
    tool_session_id = \
        db.Column(db.Integer, db.ForeignKey('tool_session.id'))

    @staticmethod
    def save_result(cls, session):
        res = ClassificationResult.create(
            mapobject_name=cls.mapobject_name, tool_session_id=session.id)

        label_objs = []
        ids = Mapobject.translate_external_ids(
            cls.ids, session.experiment_id, cls.mapobject_name)
        for ext_id, label in zip(ids, cls.labels):
            pl = ClassificationResultLabel(
                mapobject_id=ext_id, label=label,
                classification_result_id=res.id)
            label_objs.append(pl)
        db.session.add_all(label_objs)
        db.session.commit()

        return res


class ClassificationResultLabel(Model, CRUDMixin):
    id = db.Column(db.Integer, primary_key=True)
    mapobject_id = db.Column(db.Integer, db.ForeignKey('mapobject.id'))
    classification_result_id = \
        db.Column(db.Integer, db.ForeignKey('classification_result.id'))
    label = db.Column(db.Integer)
