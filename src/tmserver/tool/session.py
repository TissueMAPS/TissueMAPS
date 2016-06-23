from sqlalchemy.orm import relationship, backref
from sqlalchemy import Integer, ForeignKey, Column, String

from tmserver.model import Model


class ToolSession(Model):
    __tablename__ = 'tool_sessions'

    uuid = Column(String(50), index=True, unique=True)

    experiment_id = Column(
        Integer,
        ForeignKey('experiments.id', onupdate='CASCADE', ondelete='CASCADE')
    )

    tool_id = Column(
        Integer,
        ForeignKey('tools.id', onupdate='CASCADE', ondelete='CASCADE')
    )

    # TODO: Tool session should be linked to an saved experiment state.
    # appstate_id = Column(Integer, ForeignKey('appstates.id'))

    # appstate = relationship(
    #     'AppStateBase', uselist=False, backref=backref(
    #         'tool_instances', cascade='all, delete-orphan'))

    experiment = relationship(
        'Experiment', uselist=False,
        single_parent=True,
        backref=backref('tool_sessions', cascade='all, delete-orphan')
    )

    tool = relationship(
        'Tool', uselist=False,
        single_parent=True,
        backref=backref('sessions', cascade='all, delete-orphan')
    )

    def set(key, value):
        pass

    def get(key):
        pass
