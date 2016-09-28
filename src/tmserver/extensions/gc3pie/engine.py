from __future__ import absolute_import
from collections import defaultdict
import functools
import itertools
import time
import logging
import gc3libs
import gc3libs.core
import gc3libs.session

__docformat__ = 'reStructuredText'
__version__ = '$Revision$'

logger = logging.getLogger(__name__)


def _get_scheduler_and_lock_factory(lib):
    """Returns factories for creating a period task scheduler and locks.

    The scheduler will be a scheduler class from the APScheduler_
    framework (which see for the API), and the lock factory is an
    appropriate locking object for synchronizing independently running
    tasks.

    Parameters
    ----------
    lib: str
        ``"threading"`` or ``"gevent"``,
        each of them selects a scheduler and lock objects compatible with
        the named framework for concurrent processing

    Returns
    -------
    tuple

    Examples
    --------
    sched_factory, lock_factory = _get_scheduler_and_lock_factory("threading")
    sched = sched_factory()
    sched.add_job(task1, "interval", seconds=5)
    sched.add_job(task2, "interval", seconds=30)

    shared_data_lock = lock_factory()

    def task1():
      # ...
      with shared_data_lock:
        # modify shared data

    Raises
    ------
    NotImplementedError
        when `lib` is one of ``tornado``, ``asyncio``, ``twisted`` or ``qt``
    ValueError
        when `lib` is unknown

    .. _APScheduler: https://apscheduler.readthedocs.org/en/latest/userguide.html
    """
    if lib == 'threading':
        from apscheduler.schedulers.background import BackgroundScheduler
        from threading import Lock
        return (BackgroundScheduler, Lock)
    elif lib == 'gevent':
        from apscheduler.schedulers.gevent import GeventScheduler
        from gevent.lock import Semaphore
        return (GeventScheduler, Semaphore)
    elif lib in ['asyncio', 'tornado', 'twisted', 'qt']:
        raise NotImplemented(
            "Support for {lib} is not yet available!"
            .format(lib=lib)
        )
    else:
        raise ValueError(
            "Library '{lib}' is unknown to `{mod}._get_scheduler_and_lock_factory()`"
            .format(lib=lib, mod=__name__)
        )


def at_most_once_per_cycle(fn):
    """Ensures the decorated function is not executed more than once per
    each poll interval.

    Cached results are returned instead, if `Engine.progress()` has
    not been called in between two separate invocations of the wrapped
    function.
    """
    @functools.wraps(fn)
    def wrapper(self, *args):
        if not self._progress_last_run:
            return fn(self, *args)
        else:
            key = (fn, tuple(id(arg) for arg in args))
            try:
                update = (
                    self._cache_last_updated[key] < self._progress_last_run
                )
            except AttributeError:
                self._cache_last_updated = defaultdict(float)
                self._cache_value = dict()
                update = True
            if update:
                self._cache_value[key] = fn(self, *args)
                self._cache_last_updated[key] = time.time()
            return self._cache_value[key]
    return wrapper


class BgEngine(object):
    """A GC3Pie `Engine`:class: instance that runs in the background.

    A `BgEngine` exposes the same interface as a regular `Engine`
    class, but proxies all operations for asynchronous execution by
    the wrapped `Engine` instance.  In practice, this means that all
    invocations of `Engine` operations on a `BgEngine` always succeed:
    errors will only be visible in the background thread of execution.

    Users can define a custom callback function that gets invokes after each
    `Engine.progress()` call and applied to each task managed by the engine.
    To this end, set the attribute `progress_callback`.
    """
    def __init__(self, lib, *args, **kwargs):
        """
        Parameters
        ----------
        lib: str
            library for scheduler, either ``"threading"`` or ``"gevent"``
        args: list, optional
            additional arguments as array, the first and only element must be
            an instance of :py:class:`gc3lib.core.Engine`
        kwargs: dict, optional
            additional arguments that can be parsed to the :py:class:`Engine`
            instance as a mapping of key-value pairs
        """
        sched_factory, lock_factory = _get_scheduler_and_lock_factory(lib)
        self._scheduler = sched_factory()
        self.progress_callback = None

        self._engine_locked = lock_factory()

        # a queue for Engine ops
        self._q = []
        self._q_locked = lock_factory()

        assert len(args) > 0, (
            "`BgEngine()` must be called"
            " either with an `Engine` instance as first and only argument,"
            " or with a set of parameters to pass on to the `Engine` constructor.")
        if isinstance(args[0], gc3libs.core.Engine):
            # first (and only!) argument is an `Engine` instance, use that
            self._engine = args[0]
            assert len(args) == 1, (
                "If an `Engine` instance is passed to `BgEngine()`"
                " then it must be the only argument"
                " after the concurrency framework name.")
        else:
            # use supplied parameters to construct an `Engine`
            self._engine = gc3libs.core.Engine(*args, **kwargs)

        # no result caching until an update is really performed
        self._progress_last_run = 0

    #
    # control main loop scheduling
    #

    def start(self, interval):
        """Starts triggering the main loop every `interval` seconds.

        Parameters
        ----------
        interval: int
            looping interval for the scheduler
        """
        self.running = True
        self._scheduler.add_job(
            (lambda: self._perform()), 'interval', seconds=interval,
            # TODO: "id" to be able to later remove the job?
        )
        self._scheduler.start()
        gc3libs.log.info(
            "Started background execution of Engine %s every %d seconds",
            self._engine, interval
        )

    def stop(self, wait=False):
        """Stops background execution of the main loop.

        Parameters
        ----------
        wait: bool
            to wait until all submitted jobs have been executed

        Note
        ----
        Call :py:meth:`start` to resume running.
        """
        gc3libs.log.info(
            "Stopping background execution of Engine %s ...", self._engine
        )
        self.running = False
        self._scheduler.shutdown(wait)

    def _perform(self):
        """
        Main loop: runs in a background thread after `start`:meth: has
        been called.

        There are two tasks that this loop performs:

        - Execute any queued engine commands.

        - Run `Engine.progress()` to ensure that GC3Pie tasks are updated.
        """
        gc3libs.log.debug("%s: _perform() started", self)
        # quickly grab a local copy of the command queue, and
        # reset it to the empty list -- we do not want to hold
        # the lock on the queue for a long time, as that would
        # make the API unresponsive
        with self._q_locked:
            q = self._q
            self._q = list()

        # execute delayed operations
        for fn, args, kwargs in q:
            gc3libs.log.debug(
                "Executing delayed call %s(*%r, **%r) ...",
                fn.__name__, args, kwargs
            )
            try:
                fn(*args, **kwargs)
            except Exception, err:
                gc3libs.log.error(
                    "Got %s executing delayed call %s(*%r, **%r): %s",
                    err.__class__.__name__,
                    fn.__name__, args, kwargs,
                    err, exc_info=__debug__
                )
        # update GC3Pie tasks
        gc3libs.log.debug(
            "%s: calling `progress()` on Engine %s ...",
            self, self._engine
        )
        try:
            self._engine.progress()
            try:
                if self.progress_callback is not None:
                    for task in self.iter_tasks:
                        self.progress_callback(task)
            except Exception, err:
                gc3libs.log.error(
                    "Got %s invoking callback after `Engine.progress()`: %s",
                    err.__class__.__name__, err, exc_info=__debug__
                )
            self._progress_last_run = time.time()
        except Exception, err:
            gc3libs.log.error(
                "Got %s running `Engine.progress()` in the background: %s",
                err.__class__.__name__, err, exc_info=__debug__
            )
        gc3libs.log.debug("%s: _perform() done", self)

    #
    # Engine interface
    #

    def add(self, task):
        logger.debug('add task to engine: %s', task.persistent_id)
        with self._q_locked:
            self._q.append((self._engine.add, (task,), {}))

    def redo(self, task, index):
        logger.debug('redo task "%s" at %d', task.persistent_id, index)
        with self._q_locked:
            self._q.append((self._engine.redo, (task, index,), {}))

    def close(self):
        with self._q_locked:
            self._q.append((self._engine.close, tuple(), {}))

    def fetch_output(self, task, output_dir=None,
                     overwrite=False, changed_only=True, **extra_args):
        with self._q_locked:
            self._q.append(
                (self._engine.fetch_output,
                (task, output_dir, overwrite, changed_only), extra_args)
            )

    def free(self, task, **extra_args):
        with self._q_locked:
            self._q.append((self._engine.free, (task,), extra_args))

    def get_resources(self):
        with self._q_locked:
            self._q.append((self._engine.get_resources, tuple(), {}))

    def get_backend(self, name):
        with self._q_locked:
            self._q.append((self._engine.get_backend, (name,), {}))

    def kill(self, task, **extra_args):
        logger.debug('kill task: %s', task.persistent_id)
        with self._q_locked:
            self._q.append((self._engine.kill, (task,), extra_args))

    def peek(self, task, what='stdout', offset=0, size=None, **extra_args):
        with self._q_locked:
            self._q.append(
                (self._engine.peek,
                (task, what, offset, size), extra_args)
            )

    def progress(self):
        """
        Proxy to `Engine.progress`.

        If the background thread is already running, this is a no-op,
        as progressing tasks is already taken care of by the
        background thread.  Otherwise, just forward the call to the
        wrapped engine.
        """
        if self.running:
            pass
        else:
            self._engine.progress()

    def remove(self, task):
        logger.debug('remove task from engine: %s', task.persistent_id)
        with self._q_locked:
            self._q.append((self._engine.remove, (task,), {}))

    def select_resource(self, match):
        with self._q_locked:
            self._q.append((self._engine.select_resource, (match,), {}))

    def stats(self, only=None):
        return self._engine.stats(only)

    def submit(self, task, resubmit=False, targets=None, **extra_args):
        with self._q_locked:
            self._q.append((self._engine.submit, (task, resubmit, targets), extra_args))

    def update_job_state(self, *tasks, **extra_args):
        with self._q_locked:
            self._q.append((self._engine.update_job_state, tasks, extra_args))

    #
    # informational methods
    #

    def iter_tasks(self):
        """
        Iterate over all tasks managed by the Engine.
        """
        return itertools.chain(
            iter(self._engine._new),
            iter(self._engine._in_flight),
            iter(self._engine._stopped),
            iter(self._engine._terminating),
            iter(self._engine._terminated),
        )
