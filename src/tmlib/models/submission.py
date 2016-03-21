from sqlalchemy import Column, Integer, String, LargeBinary, ForeignKey
from sqlalchemy.orm import relationship

from tmlib.models import Model


class Submission(Model):

    '''A *submission* handles the processing of a computational *task*
    on a cluster.

    Attributes
    ----------
    task: gc3libs.Task
        submitted task
    experiment_id: int
        ID of the parent experiment
    experiment: tmlib.experiment.Experiment
        parent experiment to which the submission belongs
    user_id: int
        ID of the submitting user
    user: tmlib.user.User
        parent user to which the submission belongs
    '''

    #: Name of the corresponding database table
    __tablename__ = 'submissions'

    #: Table columns
    task_id = Column(Integer, ForeignKey('tasks.id'))
    experiment_id = Column(Integer, ForeignKey('experiments.id'))
    user_id = Column(Integer, ForeignKey('users.id'))

    #: Relationships to other tables
    experiment = relationship('Experiment', backref='submissions')
    user = relationship('User', backref='submissions')

    def __init__(self, task, experiment, user):
        '''
        Parameters
        ----------
        task: gc3libs.Task
            submitted task
        experiment: tmlib.experiment.Experiment
            parent experiment to which the submission belongs
        user: tmlib.user.User
            parent user to which the submission belongs
        '''
        self.task_id = task.id
        self.experiment_id = experiment.id
        self.user_id = user.id


class Task(Model):

    '''A *task* is a job that can be submitted to a cluster for processing
    and its state can be monitored while being processed.

    Attributes
    ----------
    state: str
        processing state
    data: gc3libs.Task
        Python object representation of the task
    '''

    #: Name of the corresponding database table
    __tablename__ = 'tasks'

    #: Table columns
    state = Column(String(128))

    #: Store for pickled Python task objects
    data = LargeBinary()
