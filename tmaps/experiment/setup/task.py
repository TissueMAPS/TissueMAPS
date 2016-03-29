from tmaps.model import Model
from tmaps.extensions import db


class TaskSubmission(Model):
    experiment_id = db.Column(
        db.Integer, db.ForeignKey('experiment.id'), primary_key=True)

    task_id = db.Column(
        db.Integer, db.ForeignKey('gc3pie_tasks.id'), primary_key=True)

    submitting_user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    submitting_user = db.relationship('User', backref='task_submissions')
    experiment = db.relationship('Experiment', backref='task_submissions')
