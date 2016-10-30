# TmLibrary - TissueMAPS library for distibuted image processing routines.
# Copyright (C) 2016  Markus D. Herrmann, University of Zurich and Robin Hafen
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
import gc3libs
from sqlalchemy import Column, Integer, String, LargeBinary, Interval, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship, backref

from tmlib.models.base import MainModel, DateMixIn


class Submission(MainModel, DateMixIn):

    '''A *submission* handles the processing of a computational *task*
    on a cluster.

    Attributes
    ----------
    experiment_id: int
        ID of the parent experiment
    experiment: tmlib.experiment.Experiment
        parent experiment to which the submission belongs
    user_id: int
        ID of the submitting user
    user: tmlib.user.User
        parent user to which the submission belongs
    '''

    __tablename__ = 'submissions'

    #: str: name of the program that submitted the tasks
    program = Column(String, index=True)

    #: int: ID of the parent experiment
    experiment_id = Column(
        Integer,
        ForeignKey(
            'experiment_references.id', onupdate='CASCADE', ondelete='CASCADE'
        ),
        index=True
    )

    #: int: ID of the top task in the submitted collection of tasks
    top_task_id = Column(
        Integer,
        index=True
    )
    # TODO: make top_task_id a foreign key and create a relationship

    #: tmlib.models.experiment.Experimment: parent experiment
    experiment = relationship(
        'ExperimentReference',
        backref=backref('submissions', cascade='all, delete-orphan')
    )


    def __init__(self, experiment_id, program):
        '''
        Parameters
        ----------
        experiment_id: int
            ID of the parent experiment
        program: str
            name of the program that submits the tasks
        '''
        self.experiment_id = experiment_id
        self.program = program

    def __repr__(self):
        return (
            '<Submission(id=%r, task=%r, experiment=%r, program=%r)>'
            % (self.id, self.task.name, self.experiment.name, self.program)
        )


# class Batch(MainModel):

#     '''A *batch* describes all inputs as well as the expected outputs of
#     an individual *task*.

#     Attributes
#     ----------
#     name: str
#         name of the corresponding task
#     job_description: dict
#         specification of inputs and outputs (and potentially other
#         parameters)
#     submission_id: int
#         ID of the parent submission
#     submission: tmlib.models.Submission
#         parent submission to which the batch belongs
#     '''

#     #: str: name of the corresponding database table
#     __tablename__ = 'batches'

#     # Table columns
#     name = Column(String, index=True)
#     description = Column(JSONB)
#     submission_id = Column(
#         Integer,
#         ForeignKey('submissions.id', onupdate='CASCADE', ondelete='CASCADE')
#     )

#     # Relationships to other tables
#     submission = relationship(
#         'Submission',
#         backref=backref('batches', cascade='all, delete-orphan')
#     )

#     def __init__(self, name, description, submission_id):
#         '''
#         Parameters
#         ----------
#         name: str
#             name of the corresponding task
#         description: dict
#             specification of inputs and outputs (and potentially other
#             parameters)
#         submission_id: int
#             ID of the parent submission

#         See also
#         --------
#         ::meth:`tmlib.workflow.api.create_batches`
#         '''
#         self.name = name
#         self.description = description
#         self.submission_id = submission_id

#     def __repr__(self):
#         return (
#             '<Batch(id=%r, name=%r, submission_id=%r)>'
#             % (self.id, self.name, self.submission_id)
#         )


class Task(MainModel):

    '''A *task* represents a computational job that can be submitted to a
    cluster for processing. Its state will be monitored while being processed.

    '''

    __tablename__ = 'tasks'

    __distribute_by_hash__ = 'id'

    #: str: procssing state, e.g. ``"RUNNING"`` or ``"TERMINATED"``
    state = Column(String, index=True)

    #: str: name given by application
    name = Column(String, index=True)

    #: int: exitcode
    exitcode = Column(Integer, index=True)

    #: datetime.timedelta: total time of task (sum of all subtasks in case
    #: of a task collection)
    time = Column(Interval, index=True)

    #: int: total memory in MG of task (sum of all subtasks in case
    #: of a task collection)
    memory = Column(Integer, index=True)

    #: datetime.timedelta: total CPU time of task (sum of all subtasks in case
    #: of a task collection)
    cpu_time = Column(Interval, index=True)

    #: str: name of the corresponding Python object
    type = Column(String, index=True)

    #: bool: whether the task is a collection of tasks
    is_collection = Column(Boolean, index=True)

    #: Pickeled Python `gc3libs.Task` or `gc3libs.workflow.TaskCollection` object
    data = Column(LargeBinary)

    #: int: ID of parent submission
    submission_id = Column(
        Integer,
        ForeignKey('submissions.id', onupdate='CASCADE', ondelete='CASCADE'),
        index=True
    )

    #: tmlib.models.submission.Submission: parent submission
    submission = relationship(
        'Submission',
        backref=backref('tasks', cascade='all, delete-orphan')
    )

    def __repr__(self):
        return (
            '<Task(id=%r, name=%r, submission_id=%r)>'
            % (self.id, self.name, self.submission_id)
        )

    @property
    def status(self):
        '''Dict[str, str or int or bool]: current task status'''
        failed = (
            self.exitcode != 0 and self.exitcode is not None
        )
        live_states = {
            gc3libs.Run.State.SUBMITTED,
            gc3libs.Run.State.RUNNING,
            gc3libs.Run.State.TERMINATING,
            gc3libs.Run.State.STOPPED
        }
        data = {
            'done': self.state == gc3libs.Run.State.TERMINATED,
            'failed': failed,
            'name': self.name,
            'state': self.state,
            'live': self.state in live_states,
            'memory': self.memory,
            'type': self.type,
            'exitcode': self.exitcode,
            'id': self.id,
            'submission_id': self.submission_id,
            'time': self.time,
            'cpu_time': self.cpu_time
        }
        # Convert timedeltas to string to make it JSON serializable
        if data['time'] is not None:
            data['time'] = str(data['time'])
        if data['cpu_time'] is not None:
            data['cpu_time'] = str(data['cpu_time'])
        return data

