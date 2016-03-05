from tmaps.extensions.database import db
from tmaps.model import CRUDMixin, Model


class ToolSession(Model, CRUDMixin):
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(50), index=True)

    experiment_id = \
        db.Column(db.Integer, db.ForeignKey('experiment.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    tool_id = db.Column(db.Integer, db.ForeignKey('tool.id'))
    appstate_id = db.Column(db.Integer, db.ForeignKey('appstate.id'))

    created_on = db.Column(db.DateTime, default=db.func.now())

    # appstate = db.relationship(
    #     'AppStateBase', uselist=False, backref=db.backref(
    #         'tool_instances', cascade='all, delete-orphan'))

    experiment = db.relationship('Experiment', uselist=False)
    user = db.relationship('User', uselist=False)

#     def __repr__(self):
#         return '<ToolInstance %s : %d>' % (self.tool_id, self.id)

#     def as_dict(self):
#         return {
#             'id': self.id,
#             'tool_id': self.tool_id,
#             'appstate_id': self.appstate_id,
#             'experiment_id': self.experiment_id,
#             'user_id': self.user_id
#         }


