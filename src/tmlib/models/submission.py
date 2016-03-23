from sqlalchemy import Column, Integer, String, LargeBinary, Interval, ForeignKey
from sqlalchemy.orm import relationship

from tmlib.models import Model, DateMixIn


class Submission(DateMixIn, Model):

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

    # Table columns
    task_id = Column(Integer, ForeignKey('tasks.id'))
    experiment_id = Column(Integer, ForeignKey('experiments.id'))
    user_id = Column(Integer, ForeignKey('users.id'))

    # Relationships to other tables
    experiment = relationship('Experiment', backref='submissions')
    user = relationship('User', backref='submissions')

    def __init__(self, task, experiment, user):
        '''
        Parameters
        ----------
        task: tmlib.models.submission.Task
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

    # Table columns
    state = Column(String)
    name = Column(String)
    exitcode = Column(Integer)
    time = Column(Interval)
    memory = Column(Integer)
    cpu_time = Column(Interval)
    data = Column(LargeBinary)
    submission_id = Column(Integer, ForeignKey('submissions.id'))

    # Relationships to other tables
    submission = relationship('Submission', backref='tasks')

    def __init__(self, state, name, exitcode, time, memory, cpu_time, data):
        '''
        Parameters
        ----------
        state: gc3libs.Run.State
            processing state of the task
        name: str
            name of the task
        exitcode: int
            return value of the submitted program
        time: datetime.timedelta
            duration of the task
        memory: int
            memory used by the task in GB
        cpu_time: datetime.timedelta
            used cpu time of the task
        data: gc3libs.Task
            task object (will get pickled)
        '''
        self.state = state
        self.name = name
        self.exitcode = exitcode
        self.time = time
        self.memory = memory
        self.cpu_time = cpu_time
        self.data = data
