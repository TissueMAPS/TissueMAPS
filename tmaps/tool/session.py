from sqlalchemy.orm import relationship
from sqlalchemy import Integer, ForeignKey, Column, String

from tmaps.model import CRUDMixin, Model


class ToolSession(Model, CRUDMixin):
    __tablename__ = 'tool_sessions'

    uuid = Column(String(50), index=True, unique=True)

    experiment_id = \
        Column(Integer, ForeignKey('experiments.id'))
    user_id = Column(Integer, ForeignKey('users.id'))
    tool_id = Column(Integer, ForeignKey('tools.id'))
    appstate_id = Column(Integer, ForeignKey('appstates.id'))

    # appstate = relationship(
    #     'AppStateBase', uselist=False, backref=backref(
    #         'tool_instances', cascade='all, delete-orphan'))

    experiment = relationship('Experiment', uselist=False)
    user = relationship('User', uselist=False)

    def set(key, value):
        pass

    def get(key):
        pass

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


