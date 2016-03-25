import gc3libs
from prettytable import PrettyTable
from tmlib.workflow import Workflow
from tmlib.workflow import ParallelWorkflowStage
from tmlib.workflow import SequentialWorkflowStage
from tmlib.workflow import WorkflowStep
from tmlib.workflow.jobs import RunJobCollection
from tmlib.workflow.jobs import MultiRunJobCollection
from tmlib.workflow.jobs import CollectJob


def format_stats_data(stats):
    '''
    For each task state (and pseudo-state like ``ok`` or
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
    '''
    Formats a timestamp in seconds to "HH:MM:SS" string.

    Parameters
    ----------
    elapsed_time: float
        timestamp

    Returns
    -------
    str
        formatted timestamp
    '''
    return '{:d}:{:02d}:{:02d}'.format(
                *reduce(
                    lambda ll, b: divmod(ll[0], b) + ll[1:],
                    [(int(elapsed_time),), 60, 60]
                ))


def get_task_data(task, description=None):
    '''
    Provide the following data for each task and recursively for each
    subtask in form of a mapping:

        * ``"name"`` (*str*): name of task
        * ``"state"`` (*g3clibs.Run.State*): state of the task
        * ``"is_live"`` (*bool*): whether the task is currently processed
        * ``"is_done"`` (*bool*): whether the task is done
        * ``"failed"`` (*bool*): whether the task failed, i.e. terminated
          with non-zero exitcode
        * ``"status_code"`` (*int*): status code returned by the program
        * ``"percent_done"`` (*float*): percent of subtasks that are *done*

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
            'time': task_.get('duration', None),
            'memory': task_.get('max_used_memory', None)
        }

        if isinstance(task_, WorkflowStep):
            job_type = 'step'
        elif (isinstance(task_, ParallelWorkflowStage) or
                isinstance(task_, SequentialWorkflowStage)):
            job_type = 'stage'
        elif isinstance(task_, Workflow):
            job_type = 'workflow'
        elif isinstance(task, CollectJob):
            job_type = 'phase/job'
        elif (isinstance(task_, RunJobCollection) or
                isinstance(task_, MultiRunJobCollection)):
            job_type = 'phase'
        else:
            job_type = 'job'

        data['type'] = job_type

        done = 0.0
        if isinstance(task_, gc3libs.workflow.TaskCollection):
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
            else:
                data['percent_done'] = 0
        elif isinstance(task_, gc3libs.Task):
            # For an individual task it is difficult to estimate to which
            # extent the task has been completed. For simplicity and
            # consistency, we just set "percent_done" to 100% once the job
            # is TERMINATED and 0% otherwise
            if task_.execution.state == gc3libs.Run.State.TERMINATED:
                data['percent_done'] = 100
        else:
            raise NotImplementedError(
                'Unhandled task class %r' % (task_.__class__))

        if task_.execution.state == gc3libs.Run.State.TERMINATED:
            if not data['time']:
                # In case duration is not provided, e.g. on localhost
                data['time'] = format_timestamp(
                        task_.execution.state_last_changed -
                        task_.execution.timestamp['SUBMITTED']
                )

        if isinstance(task_, gc3libs.workflow.TaskCollection):
            # loop recursively over subtasks
            data['subtasks'] = [get_info(t, i+1) for t in task_.tasks]

        return data

    return get_info(task, 0)


def print_task_status(task_data, monitoring_depth):
    '''
    Pretty print the status of a submitted GC3Pie tasks to the console in
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
            data['time'] if data['time'] is not None else '',
            data['memory'] if data['memory'] is not None else '',
            data['exitcode'] if data['exitcode'] is not None else '',
            data['id']
        ])
        if i < monitoring_depth:
            for subtd in data.get('subtasks', list()):
                add_row_recursively(subtd, table, i+1)
    x = PrettyTable([
            'Name', 'Type', 'State', 'Done (%)',
            'Time (HH:MM:SS)', 'Memory (KB)', 'ExitCode', 'ID'
    ])
    x.align['Name'] = 'l'
    x.align['Type'] = 'l'
    x.align['State'] = 'l'
    x.align['Done (%)'] = 'r'
    x.align['Memory (KB)'] = 'r'
    x.align['ID'] = 'r'
    x.padding_width = 1
    add_row_recursively(task_data, x, 0)
    print x


def log_task_status(task_data, logger, monitoring_depth):
    '''
    Log the status of a submitted GC3Pie task.

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
        logger.info('%s: %s (%.2f %%)',
                    data['name'], data['state'],
                    data['percent_done'])
        if i < monitoring_depth:
            for subtd in data.get('subtasks', list()):
                log_recursive(subtd, i+1)
    log_recursive(task_data, 0)


def log_task_failure(task_data, logger):
    '''
    Log the failure of a submitted GC3Pie task.

    Parameters
    ----------
    task_data: dict
        information about each task and its subtasks
    logger: logging.Logger
        configured logger instance
    '''
    def log_recursive(data, i):
        if data['failed']:
            logger.error('%s (id: %s) failed with exitcode %s',
                         data['name'], data['id'], data['exitcode'])
        for subtd in data.get('subtasks', list()):
            log_recursive(subtd, i+1)
    log_recursive(task_data, 0)
