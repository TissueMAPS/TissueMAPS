# TmLibrary - TissueMAPS library for distibuted image analysis routines.
# Copyright (C) 2016  Markus D. Herrmann, University of Zurich and Robin Hafen
# Copyright (C) 2018  University of Zurich
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
import logging
import datetime
from prettytable import PrettyTable
from datetime import datetime
from datetime import timedelta

import gc3libs
from gc3libs.quantity import Memory
from gc3libs.session import Session
from gc3libs.url import Url
from gc3libs.persistence.sql import make_sqlstore

import tmlib.models as tm
from tmlib import cfg

logger = logging.getLogger(__name__)


def _get_task_time(task, attr):
    def get_recursive(_task, duration):
        if hasattr(_task, 'tasks'):
            if len(_task.tasks) > 0:
                duration += sum(
                    (get_recursive(t, duration) for t in _task.tasks),
                    timedelta())
        else:
            if hasattr(_task.execution, attr):
                duration += getattr(_task.execution, attr).to_timedelta()
        return duration
    return get_recursive(task, timedelta())


def _get_task_memory(task, attr):
    def get_recursive(_task, memory):
        if hasattr(_task, 'tasks'):
            if len(_task.tasks) > 0:
                memory += sum(
                    (get_recursive(t, memory) for t in _task.tasks),
                    0)
        else:
            if hasattr(_task.execution, attr):
                memory += getattr(_task.execution, attr).amount(Memory.MB)
        return memory
    return get_recursive(task, 0)


def get_gc3pie_store_extra_fields():
    '''
    Return the "extra fields" argument for constructing a `gc3libs.SqlStore`:class:.

    This method has been factored out of `create_gc3pie_sql_store()`
    to be used in contexts where we need additional flexibility in
    creating the SQL store.
    '''
    table_columns = tm.Task.__table__.columns
    return {
        table_columns['name']: lambda task: task.jobname,
        table_columns['exitcode']: lambda task: task.execution.exitcode,
        table_columns['time']: lambda task: _get_task_time(task, 'duration'),
        table_columns['memory']: lambda task: _get_task_memory(task, 'max_used_memory'),
        table_columns['cpu_time']: lambda task: _get_task_time(task, 'used_cpu_time'),
        table_columns['submission_id']: lambda task: task.submission_id,
        table_columns['parent_id']: lambda task: task.parent_id,
        table_columns['is_collection']: lambda task: hasattr(task, 'tasks'),
        table_columns['type']: lambda task: type(task).__name__,
        # FIXME: this is still incorrect if the task's state gets
        # reset to ``NEW`` (as happens in `.redo()`) but still better
        # than the previous code which would use the timestamp of the
        # time this `create_gc3pie_store()` function was invoked...
        table_columns['created_at']: lambda task: datetime.fromtimestamp(task.execution.timestamp.get('NEW', 0)),
        table_columns['updated_at']: lambda task: datetime.now(),
    }


def create_gc3pie_sql_store():
    '''Creates a `Store` instance for job persistence in the PostgreSQL table
    :class:`Tasks <tmlib.models.submission.Tasks>`.

    Returns
    -------
    gc3libs.persistence.sql.SqlStore
        `GC3Pie` store

    Warning
    -------
    The "tasks" table must already exist.
    '''
    logger.debug('create GC3Pie store using "tasks" table')
    store_url = Url(cfg.db_master_uri)
    return make_sqlstore(
        url=store_url,
        table_name='tasks',
        extra_fields=get_gc3pie_store_extra_fields(),
    )


def create_gc3pie_session(location, store):
    '''Creates a `Session` instance for job persistence in the PostgresSQL table

    Parameters
    ----------
    location: str
        path to a directory on disk for the file system representation of the
        store
    store: gc3libs.persistence.store.Store
        store instance

    Returns
    -------
    gc3libs.persistence.session.Session
        `GC3Pie` session
    '''
    logger.debug('create GC3Pie session')
    return Session(location, store=store)


def create_gc3pie_engine(store):
    '''Creates an `Engine` instance for submitting jobs for parallel
    processing.

    Parameters
    ----------
    store: gc3libs.persistence.store.Store
        GC3Pie store object

    Returns
    -------
    gc3libs.core.Engine
        engine
    '''
    logger.debug('create GC3Pie engine')
    n = cfg.resource.max_cores * 2
    logger.debug('set maximum number of submitted jobs to %d', n)
    engine = gc3libs.create_engine(
        store=store, max_in_flight=n, max_submitted=n, forget_terminated=True
    )
    # Put all output files in the same directory
    logger.debug('store stdout/stderr in common output directory')
    engine.retrieve_overwrites = True
    return engine


def format_stats_data(stats):
    '''For each task state (and pseudo-state like ``ok`` or
    ``failed``), two values are returned: the count of managed
    tasks that were in that state when `Engine.progress()` was
    last run, and what percentage of the total managed tasks this
    is.

    Parameters
    ----------
    stats: gc3libs.core.Engine
        as returned by :meth:`gc3libs.core.Engine.stats()`

    Returns
    -------
    dict
        global statistics about the jobs in the :class:`Engine`
    '''
    data = {}
    tot = stats['total']
    for state, count in stats.items():
        data['count_' + state.lower()] = count
        data['percent_' + state.lower()] = 100.0 * count / max(tot, 1)
    return data


def format_timestamp(elapsed_time):
    '''Formats a timestamp in seconds to "HH:MM:SS" string.

    Parameters
    ----------
    elapsed_time: float
        elapsed time in seconds

    Returns
    -------
    str
        formatted timestamp
    '''
    return '{:d}:{:02d}:{:02d}'.format(
        *reduce(
            lambda ll, b: divmod(ll[0], b) + ll[1:],
            [(int(elapsed_time),), 60, 60]
        )
    )


def format_task_data(name, type, created_at, updated_at, state, exitcode,
        memory, time, cpu_time):
    '''Formats task data in the way expected by clients:

        * ``name`` (*str*): name of task
        * ``type`` (*str*): type of the task object
        * ``created_at`` (*str*): date and time when task was created
        * ``updated_at`` (*str*): date and time when task was last updated
        * ``state`` (*str*): state of the task
        * ``live`` (*bool*): whether the task is currently processed
        * ``done`` (*bool*): whether the task is done
        * ``failed`` (*bool*): whether the task failed, i.e. terminated
          with non-zero exitcode
        * ``percent_done`` (*float*): percent of subtasks that are *done*
        * ``exitcode`` (*int*): status code returned by the program
        * ``time`` (*str*): duration as "HH:MM:SS"
        * ``memory`` (*float*): amount of used memory in MB
        * ``cpu_time`` (*str*): used cpu time as "HH:MM:SS"

    Parameters
    ----------
    name: str
    type: str
    created_at: datetime.datetime
    updated_at: datetime.datetime
    state: g3clibs.Run.State
    exitcode: int
    memory: str
    time: str
    cpu_time: str

    Returns
    -------
    Dict[str, Union[str, int, bool]]
    '''
    datetime_format = '%Y-%m-%d %H:%M:%S'
    failed = (
        exitcode != 0 and exitcode is not None
    )
    live_states = {
        gc3libs.Run.State.SUBMITTED,
        gc3libs.Run.State.RUNNING,
        gc3libs.Run.State.TERMINATING,
        gc3libs.Run.State.STOPPED
    }
    data = {
        'done': state == gc3libs.Run.State.TERMINATED,
        'failed': failed,
        'created_at': created_at.strftime(datetime_format),
        'updated_at': updated_at.strftime(datetime_format),
        'name': name,
        'state': state,
        'live': state in live_states,
        'memory': memory,
        'type': type,
        'exitcode': exitcode,
        'time': time,
        'cpu_time': cpu_time
    }
    # Convert timedeltas to string to make it JSON serializable
    if data['time'] is not None:
        data['time'] = str(data['time'])
    if data['cpu_time'] is not None:
        data['cpu_time'] = str(data['cpu_time'])
    return data


def get_task_status_recursively(task_id, recursion_depth=None, id_encoder=None):
    '''Provides status information for each task and recursively for subtasks.

    Parameters
    ----------
    task: gc3libs.workflow.TaskCollection or gc3libs.Task
        submitted highest level GC3Pie task
    recursion_depth: int, optional
        recursion depth for subtask querying; by default
        data of all subtasks will be queried (default: ``None``)
    id_encoder: function, optional
        function that encodes task IDs

    Returns
    -------
    dict
        information about each task and its subtasks

    See also
    --------
    :func:`tmlib.workflow.utils.format_task_data`
    '''
    logger.debug('get task status recursively')
    def get_info(task_id_, i):

        data = dict()
        if recursion_depth is not None:
            if i > recursion_depth:
                return

        with tm.utils.MainSession() as session:
            task = session.query(
                tm.Task.name, tm.Task.type,
                tm.Task.created_at, tm.Task.updated_at, tm.Task.state,
                tm.Task.exitcode, tm.Task.memory, tm.Task.time,
                tm.Task.cpu_time, tm.Task.is_collection
            ).\
            filter_by(id=task_id_).\
            one()

            data = format_task_data(
                task.name, task.type, task.created_at, task.updated_at,
                task.state, task.exitcode,
                task.memory, task.time, task.cpu_time
            )

        data['id'] = task_id_
        if id_encoder is not None:
            data['id'] = id_encoder(data['id'])

        if task.is_collection:
            done = 0.0
            with tm.utils.MainSession() as session:
                subtasks = session.query(
                    tm.Task.id,
                    tm.Task.name, tm.Task.type,
                    tm.Task.created_at, tm.Task.updated_at, tm.Task.state,
                    tm.Task.exitcode, tm.Task.memory, tm.Task.time,
                    tm.Task.cpu_time, tm.Task.is_collection
                ).\
                filter_by(parent_id=task_id_).\
                order_by(tm.Task.id).\
                all()

                subtask_ids = []
                for t in subtasks:
                    subtask_ids.append(t.id)
                    if t.state == gc3libs.Run.State.TERMINATED:
                        done += 1
                if len(subtasks) > 0:
                    data['percent_done'] = done / len(subtasks) * 100
                else:
                    data['percent_done'] = 0

            data['n_subtasks'] = len(subtasks)
            data['subtasks'] = [get_info(tid, i+1) for tid in subtask_ids]

        else:
            if task.state == gc3libs.Run.State.TERMINATED:
                data['percent_done'] = 100
            else:
                data['percent_done'] = 0

            data['n_subtasks'] = 0
            data['subtasks'] = []

        return data

    return get_info(task_id, 0)


def print_task_status(task_info):
    '''Pretty prints the status of a submitted GC3Pie tasks to the console in
    table format.

    Parameters
    ----------
    task_info: dict
        information about each task and its subtasks

    See also
    --------
    :func:`tmlib.workflow.utils.get_task_status_recursively`
    '''
    def add_row_recursively(data, table, i):
        table.add_row([
            data['id'],
            data['name'],
            data['type'],
            data['state'],
            '%.2f' % data['percent_done'],
            data['exitcode'] if data['exitcode'] is not None else '',
            data['time'] if data['time'] is not None else '',
            data['memory'] if data['memory'] is not None else '',
            data['cpu_time'] if data['cpu_time'] is not None else ''
        ])
        for subtd in data.get('subtasks', list()):
            if subtd is None:
                continue
            add_row_recursively(subtd, table, i+1)
    x = PrettyTable([
            'ID', 'Name', 'Type', 'State', 'Done (%)', 'ExitCode',
            'Time (HH:MM:SS)', 'Memory (MB)', 'CPU Time (HH:MM:SS)'
    ])
    x.align['ID'] = 'r'
    x.align['Name'] = 'l'
    x.align['Type'] = 'l'
    x.align['State'] = 'l'
    x.align['Done (%)'] = 'r'
    x.align['Memory (MB)'] = 'r'
    x.padding_width = 1
    add_row_recursively(task_info, x, 0)
    print x


def log_task_status(task_info, logger, monitoring_depth):
    '''Logs the status of a submitted GC3Pie task.

    Parameters
    ----------
    task_info: dict
        information about each task and its subtasks
    logger: logging.Logger
        configured logger instance
    monitoring_depth: int
        recursion depth for subtask querying
    '''
    def log_recursive(data, i):
        logger.info(
            '%s: %s (%.2f %%)',
            data['name'], data['state'], data['percent_done']
        )
        if i < monitoring_depth:
            for subtd in data.get('subtasks', list()):
                log_recursive(subtd, i+1)
    log_recursive(task_info, 0)


def log_task_failure(task_info, logger):
    '''Logs the failure of a submitted GC3Pie task.

    Parameters
    ----------
    task_info: dict
        information about each task and its subtasks
    logger: logging.Logger
        configured logger instance
    '''
    def log_recursive(data, i):
        if data['failed']:
            logger.error(
                '%s (id: %s) failed with exitcode %s',
                 data['name'], data['id'], data['exitcode']
            )
        for subtd in data.get('subtasks', list()):
            log_recursive(subtd, i+1)
    log_recursive(task_info, 0)
