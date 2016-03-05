from tmaps.extensions.database import db
from tmaps.model import CRUDMixin, Model


class ClassificationResult(Model, CRUDMixin):
    __tablename__ = 'classification_result'
    id = db.Column(db.Integer, primary_key=True)
    mapobject_name = db.Column(db.String(120))
    tool_session_id = \
        db.Column(db.Integer, db.ForeignKey('tool_session.id'))

    @staticmethod
    def save_result(session, cls):
        res = ClassificationResult.create(
            mapobject_name=cls.mapobject_name, tool_session_id=session.id)

        label_objs = []
        for ext_id, label in zip(cls.ids, cls.labels):
            pl = PredictedLabel(
                mapobject_id=ext_id, label=label,
                classification_result_id=res.id)
            label_objs.append(pl)
        db.session.add_all(label_objs)


class PredictedLabel(Model, CRUDMixin):
    id = db.Column(db.Integer, primary_key=True)
    mapobject_id = db.Column(db.Integer, db.ForeignKey('mapobject.id'))
    classification_result_id = db.Column(db.Integer, db.ForeignKey('classification_result.id'))
    label = db.Column(db.Integer)
