from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship

from tmlib.models.base import Model


class TaskSubmission(Model):
    __tablename__ = 'task_submissions'

    task_id = Column(Integer, ForeignKey('gc3pie_tasks.id'))

    experiment_id = Column(Integer, ForeignKey('experiments.id'))
    experiment = relationship('Experiment', backref='task_submissions')

    submitting_user_id = Column(Integer, ForeignKey('users.id'))
    submitting_user = relationship('User', backref='task_submissions')
