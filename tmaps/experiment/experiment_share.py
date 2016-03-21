from sqlalchemy import Integer, ForeignKey, Column
from sqlalchemy.orm import relationship
from tmaps.model import CRUDMixin, Model


class ExperimentShare(Model, CRUDMixin):
    __tablename__ = 'experiment_shares'

    recipient_user_id = Column(
        Integer, ForeignKey('users.id'), primary_key=True)
    donor_user_id = Column(
        Integer, ForeignKey('users.id'), primary_key=True)
    experiment_id = Column(
        Integer, ForeignKey('experiments.id'), primary_key=True)
    experiment = relationship('Experiment', uselist=False)
