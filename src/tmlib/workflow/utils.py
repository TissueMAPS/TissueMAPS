import gc3libs
import numpy as np
from prettytable import PrettyTable

import tmlib.models as tm


def format_stats_data(stats):
    '''For each task state (and pseudo-state like ``ok`` or
    ``failed``), two values are returned: the count of managed
    tasks that were in that state when `Engine.progress()` was
    last run, and what percentage of the total managed tasks this
    is.

    Parameters
    ----------
    stats: gc3libs.core.Engine
        as returned by :py:meth:`gc3libs.core.Engine.stats()`

    Returns
    -------
    dict
        global statistics about the jobs in the :py:class:`Engine`
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


def get_task_data_from_engine(task):
    '''Provides the following data for each task and recursively for each
    subtask in form of a mapping:

        * ``"name"`` (*str*): name of task
        * ``"state"`` (*g3clibs.Run.State*): state of the task
        * ``"is_live"`` (*bool*): whether the task is currently processed
        * ``"is_done"`` (*bool*): whether the task is done
        * ``"failed"`` (*bool*): whether the task failed, i.e. terminated
          with non-zero exitcode
        * ``"exitcode"`` (*int*): status code returned by the program
        * ``"percent_done"`` (*float*): percent of subtasks that are *done*
        * ``"time"`` (*str*): duration as "HH:MM:SS"
        * ``"memory"`` (*float*): amount of used memory in MB
        * ``"cpu_time"`` (*str*): used cpu time as "HH:MM:SS"
        * ``"type"`` (*str*): type of the task object

    Parameters
    ----------
    task: gc3libs.workflow.TaskCollection or gc3libs.Task
        submitted GC3Pie task that should be monitored

    Returns
    -------
    dict
        information about each task and its subtasks
    '''
    # TODO: Implement WAITING state for stages/steps that are not yet created
    def get_info(task_, i):
        is_live_states = {
            gc3libs.Run.State.SUBMITTED,
            gc3libs.Run.State.RUNNING,
            gc3libs.Run.State.STOPPED
        }
        is_done = task_.execution.state == gc3libs.Run.State.TERMINATED
        failed = task_.execution.exitcode != 0
        data = {
            'id': str(task_),
            'name': task_.jobname,
            'state': task_.execution.state,
            'is_live': task_.execution.state in is_live_states,
            'is_done': is_done,
            'failed': is_done and failed,
            'exitcode': task_.execution.exitcode,
            'percent_done': 0.0,  # fix later, if possible
            'time': task_.execution.get('duration', None),
            'memory': task_.execution.get('max_used_memory', None),
            'cpu_time': task_.execution.get('used_cpu_time', None)
        }

        data['type'] = type(task_).__name__

        done = 0.0
        if hasattr(task_, 'tasks'):
            for child in task_.tasks:
                if (child.execution.state == gc3libs.Run.State.TERMINATED):
                    done += 1
            if len(task_.tasks) > 0:
                if hasattr(task_, '_tasks_to_process'):
                    # Custom sequential task collection classes build the task
                    # list dynamically, so we have to use the number of tasks
                    # that should ultimately be processed to provide an
                    # accurate "percent_done" value.
                    total = len(getattr(task_, '_tasks_to_process'))
                else:
                    total = len(task_.tasks)
                data['percent_done'] = done / total * 100
                data['time'] = np.sum([
                    t.execution.get(
                        'duration',
                        gc3libs.quantity.Duration(0, gc3libs.quantity.seconds)
                    )
                    for t in task_.tasks
                ])
                if data['time'].amount(gc3libs.quantity.seconds) == 0:
                    data['time'] = None
                else:
                    data['time'] = str(gc3libs.quantity.Duration.to_timedelta(
                        data['time']
                    ))
                data['cpu_time'] = np.sum([
                    t.execution.get(
                        'used_cpu_time',
                        gc3libs.quantity.Duration(0, gc3libs.quantity.seconds)
                    )
                    for t in task_.tasks
                ])
                if data['cpu_time'].amount(gc3libs.quantity.seconds) == 0:
                    data['cpu_time'] = None
                else:
                    data['cpu_time'] = str(gc3libs.quantity.Duration.to_timedelta(
                        data['cpu_time']
                    ))
            else:
                data['percent_done'] = 0

        else:
            # For an individual task it is difficult to estimate to which
            # extent the task has been completed. For simplicity and
            # consistency, we just set "percent_done" to 100% once the job
            # is TERMINATED and 0% otherwise
            if task_.execution.state == gc3libs.Run.State.TERMINATED:
                data['percent_done'] = 100
                if data['time'] is not None:
                    data['time'] = str(gc3libs.quantity.Duration.to_timedelta(
                        data['time']
                    ))
                if data['cpu_time'] is not None:
                    data['cpu_time'] = str(gc3libs.quantity.Duration.to_timedelta(
                        data['cpu_time']
                    ))
                if data['memory'] is not None:
                    data['memory'] = data['memory'].amount(
                        gc3libs.quantity.Memory.MB
                    )

        if hasattr(task_, 'tasks'):
            # loop recursively over subtasks
            data['subtasks'] = [get_info(t, i+1) for t in task_.tasks]

        return data

    return get_info(task, 0)


def get_task_data_from_db(task):
    '''Provides the following data for each task and recursively for each
    subtask in form of a mapping:

        * ``"name"`` (*str*): name of task
        * ``"state"`` (*g3clibs.Run.State*): state of the task
        * ``"is_live"`` (*bool*): whether the task is currently processed
        * ``"is_done"`` (*bool*): whether the task is done
        * ``"failed"`` (*bool*): whether the task failed, i.e. terminated
          with non-zero exitcode
        * ``"percent_done"`` (*float*): percent of subtasks that are *done*
        * ``"exitcode"`` (*int*): status code returned by the program
        * ``"time"`` (*str*): duration as "HH:MM:SS"
        * ``"memory"`` (*float*): amount of used memory in MB
        * ``"cpu_time"`` (*str*): used cpu time as "HH:MM:SS"
        * ``"type"`` (*str*): type of the task object

    Parameters
    ----------
    task: gc3libs.workflow.TaskCollection or gc3libs.Task
        submitted GC3Pie task that should be monitored

    Returns
    -------
    dict
        information about each task and its subtasks
    '''
    def get_info(task_, i):
        is_live_states = {
            gc3libs.Run.State.SUBMITTED,
            gc3libs.Run.State.RUNNING,
            gc3libs.Run.State.STOPPED
        }
        data = dict()
        with tm.utils.Session() as session:
            task_info = session.query(tm.Task).get(task_.persistent_id)
            data['is_done'] = task_info.state == gc3libs.Run.State.TERMINATED
            data['failed'] = task_info.exitcode != 0
            data['name'] = task_info.name
            data['state'] = task_info.state
            data['memory'] = task_info.memory
            data['type'] = task_info.type
            data['exitcode'] = task_info.exitcode
            data['id'] = task_info.id
            data['time'] = task_info.time
            # Convert timedeltas to string to make it JSON serializable
            if data['time'] is not None:
                data['time'] = str(data['time'])
            data['cpu_time'] = task_info.cpu_time
            if data['cpu_time'] is not None:
                data['cpu_time'] = str(data['cpu_time'])

            if hasattr(task_, 'tasks'):
                done = 0.0
                for t in task_.tasks:
                    t_info = session.query(tm.Task).get(t.persistent_id)
                    if t_info.state == gc3libs.Run.State.TERMINATED:
                        done += 1
                if len(task_.tasks) > 0:
                    data['percent_done'] = done / len(task_.tasks) * 100
                else:
                    data['percent_done'] = 0
            else:
                if task_info.state == gc3libs.Run.State.TERMINATED:
                    data['percent_done'] = 100
                else:
                    data['percent_done'] = 0

            if hasattr(task_, 'tasks'):
                data['subtasks'] = [get_info(t, i+1) for t in task_.tasks]

        return data

    return get_info(task, 0)


def print_task_status(task_data, monitoring_depth):
    '''Pretty prints the status of a submitted GC3Pie tasks to the console in
    table format.

    Parameters
    ----------
    task_data: dict
        information about each task and its subtasks
    monitoring_depth: int
        recursion depth for subtask querying
    '''
    # TODO: this could be read from the "tasks" table directly
    def add_row_recursively(data, table, i):
        table.add_row([
            data['name'],
            data['type'],
            data['state'],
            '%.2f' % data['percent_done'],
            data['exitcode'] if data['exitcode'] is not None else '',
            data['time'] if data['time'] is not None else '',
            data['memory'] if data['memory'] is not None else '',
            data['cpu_time'] if data['cpu_time'] is not None else '',
            data['id']
        ])
        if i < monitoring_depth:
            for subtd in data.get('subtasks', list()):
                add_row_recursively(subtd, table, i+1)
    x = PrettyTable([
            'Name', 'Type', 'State', 'Done (%)', 'ExitCode',
            'Time (HH:MM:SS)', 'Memory (MB)', 'CPU Time (HH:MM:SS)', 'ID'
    ])
    x.align['Name'] = 'l'
    x.align['Type'] = 'l'
    x.align['State'] = 'l'
    x.align['Done (%)'] = 'r'
    x.align['Memory (MB)'] = 'r'
    x.align['ID'] = 'r'
    x.padding_width = 1
    add_row_recursively(task_data, x, 0)
    print x


def log_task_status(task_data, logger, monitoring_depth):
    '''Logs the status of a submitted GC3Pie task.

    Parameters
    ----------
    task_data: dict
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
    log_recursive(task_data, 0)


def log_task_failure(task_data, logger):
    '''Logs the failure of a submitted GC3Pie task.

    Parameters
    ----------
    task_data: dict
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
    log_recursive(task_data, 0)
