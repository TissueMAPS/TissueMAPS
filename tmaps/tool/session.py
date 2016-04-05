from sqlalchemy.orm import relationship
from sqlalchemy import Integer, ForeignKey, Column, String

from tmaps.model import Model


class ToolSession(Model):
    __tablename__ = 'tool_sessions'

    uuid = Column(String(50), index=True, unique=True)

    experiment_id = \
        Column(Integer, ForeignKey('experiments.id'))

    tool_id = Column(Integer, ForeignKey('tools.id'))

    # TODO: Tool session should be linked to an saved experiment state.
    # appstate_id = Column(Integer, ForeignKey('appstates.id'))

    # appstate = relationship(
    #     'AppStateBase', uselist=False, backref=backref(
    #         'tool_instances', cascade='all, delete-orphan'))

    experiment = relationship(
        'Experiment', uselist=False, cascade='all, delete-orphan',
        single_parent=True, backref='tool_sessions')

    tool = relationship(
        'Tool', uselist=False, cascade='all, delete-orphan',
        single_parent=True, backref='sessions')

    def set(key, value):
        pass

    def get(key):
        pass
