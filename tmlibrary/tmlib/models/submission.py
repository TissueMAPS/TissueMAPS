# TmLibrary - TissueMAPS library for distibuted image analysis routines.
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
from sqlalchemy import (
    Column, Integer, BigInteger, String, LargeBinary, Interval, ForeignKey,
    Boolean
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship, backref

from tmlib.models.base import MainModel, DateMixIn


class Submission(MainModel, DateMixIn):

    '''A *submission* handles the processing of a computational *task*
    on a cluster.
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

    #: int: ID of the submitting user
    user_id = Column(
        Integer,
        ForeignKey(
            'users.id', onupdate='CASCADE', ondelete='CASCADE'
        ),
        index=True

    )

    id = Column(BigInteger, primary_key=True, autoincrement=True, index=True)

    #: int: ID of the top task in the submitted collection of tasks
    top_task_id = Column(BigInteger, index=True)
    # TODO: make top_task_id a foreign key and create a relationship

    #: tmlib.models.experiment.Experimment: parent experiment
    experiment = relationship(
        'ExperimentReference',
        backref=backref('submissions', cascade='all, delete-orphan')
    )

    #: tmlib.models.user.User: submitting user
    user = relationship(
        'User',
        backref=backref('submissions', cascade='all, delete-orphan')
    )

    def __init__(self, experiment_id, program, user_id):
        '''
        Parameters
        ----------
        experiment_id: int
            ID of the parent experiment
        program: str
            name of the program that submits the tasks
        user_id: int
            ID of the submitting user
        '''
        self.experiment_id = experiment_id
        self.program = program
        self.user_id = user_id

    def __repr__(self):
        return (
            '<Submission(id=%r, experiment_id=%r, program=%r, user_id=%r)>' % (
                self.id, self.experiment_id, self.program, self.user_id
            )
        )


class Task(MainModel, DateMixIn):

    '''A *task* represents a computational job that can be submitted to
    computational resources for processing.
    Its state will be monitored while being processed and statistics will be
    collected.

    Warning
    -------
    This table is managed by GC3Pie. Don't modify it manually!
    '''

    __tablename__ = 'tasks'

    #: str: procssing state, e.g. ``"RUNNING"`` or ``"TERMINATED"``
    state = Column(String, index=True)

    #: str: name given by application
    name = Column(String, index=True)

    #: int: exitcode
    exitcode = Column(Integer, index=True)

    #: datetime.timedelta: total time of task
    time = Column(Interval)

    #: int: total memory in MB of task
    memory = Column(Integer)

    #: datetime.timedelta: total CPU time of task
    cpu_time = Column(Interval)

    #: str: name of the corresponding Python object
    type = Column(String, index=True)

    #: bool: whether the task is a collection of tasks
    is_collection = Column(Boolean, index=True)

    #: int: ID of the parent task
    parent_id = Column(BigInteger, index=True)

    #: "Pickled" Python `gc3libs.Task` object
    data = Column(LargeBinary)

    #: int: ID of parent submission
    submission_id = Column(BigInteger, index=True)

    def __repr__(self):
        return (
            '<Task(id=%r, name=%r, submission_id=%r)>'
            % (self.id, self.name, self.submission_id)
        )
