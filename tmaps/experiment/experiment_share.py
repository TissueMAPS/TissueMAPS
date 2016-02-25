from tmaps.extensions.database import db
from tmaps.model import CRUDMixin, Model


class ExperimentShare(Model, CRUDMixin):
    recipient_user_id = db.Column(db.Integer, db.ForeignKey('user.id'),
                                  primary_key=True)
    donor_user_id = db.Column(db.Integer, db.ForeignKey('user.id'),
                              primary_key=True)
    experiment_id = db.Column(db.Integer, db.ForeignKey('experiment.id'),
                              primary_key=True)
    experiment = db.relationship('Experiment', uselist=False)

