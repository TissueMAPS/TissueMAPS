from sqlalchemy.orm import relationship, backref
from sqlalchemy import Integer, ForeignKey, Column, String

from tmlib.models import ExperimentModel


class ToolSession(ExperimentModel):

    '''A tool session deals with tool requests sent by the client and persists
    them on disk.

    Attributes
    ----------
    uuid: int
        universally unique identifier
    '''

    __tablename__ = 'tool_sessions'

    uuid = Column(String(50), index=True, unique=True)

    # TODO: Tool session should be linked to an saved experiment state.
    # appstate_id = Column(Integer, ForeignKey('appstates.id'))

    # appstate = relationship(
    #     'AppStateBase', uselist=False, backref=backref(
    #         'tool_instances', cascade='all, delete-orphan'))

    def set(key, value):
        pass

    def get(key):
        pass
