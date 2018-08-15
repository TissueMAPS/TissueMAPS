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
import sys
import logging

#: dict[int, int]: Mapping of logging verbosity to logging level
VERBOSITY_TO_LEVELS = {
    0: logging.NOTSET,  # Nothing gets logged
    1: logging.WARN,  # For simplicity. Includes ERROR, CRITICAL
    2: logging.INFO,
    3: logging.DEBUG,
}

#: dict[int, int]: Mapping of logging level to logging verbosity
LEVELS_TO_VERBOSITY = {
    logging.NOTSET: 0,
    logging.WARN: 1,
    logging.ERROR: 1,
    logging.CRITICAL: 1,
    logging.INFO: 2,
    logging.DEBUG: 3,
}


def map_logging_verbosity(verbosity):
    '''Maps logging verbosity to a level as expected by the `logging` module.

    Parameters
    ----------
    verbosity: int
        logging verbosity

    Returns
    -------
    int
        logging level

    Raises
    ------
    TypeError
        when `verbosity` doesn't have type int
    ValueError
        when `verbosity` is negative

    See also
    --------
    :attr:`tmlib.log.VERBOSITY_TO_LEVELS`
    '''
    if not isinstance(verbosity, int):
        raise TypeError('Argument "verbosity" must have type int.')
    if not verbosity >= 0:
        raise ValueError('Argument "verbosity" must be a positive number.')
    if verbosity >= len(VERBOSITY_TO_LEVELS):
        verbosity = len(VERBOSITY_TO_LEVELS) - 1
    return VERBOSITY_TO_LEVELS.get(verbosity)


def configure_logging():
    '''Configures the root logger for command line applications.

    Two stream handlers will be added to the logger:
        * "out" that will direct INFO & DEBUG messages to the standard output
        stream
        * "err" that will direct WARN, WARNING, ERROR, & CRITICAL messages to
        the standard error stream

    Note
    ----
    The level for individual loggers can be fine-tuned as follows (exemplified
    for the `tmlib` logger)::

        import logging

        logger = logging.getLogger('tmlib')
        logger.setLevel(logging.INFO)


    Warning
    -------
    Logging should only be configured once at the main entry point of the
    application!
    '''
    fmt = '[%(process)6d/%(threadName)-12s] %(asctime)s | %(levelname)-8s | %(name)-40s | %(message)s'
    datefmt = '%Y-%m-%d %H:%M:%S'
    formatter = logging.Formatter(fmt=fmt, datefmt=datefmt)

    logger = logging.getLogger()  # returns the root logger

    stderr_handler = logging.StreamHandler(stream=sys.stderr)
    stderr_handler.name = 'err'
    stderr_handler.setLevel(logging.WARN)
    stderr_handler.setFormatter(formatter)
    logger.addHandler(stderr_handler)

    stdout_handler = logging.StreamHandler(stream=sys.stdout)
    stdout_handler.name = 'out'
    stdout_handler.setFormatter(formatter)
    stdout_handler.setLevel(0)
    stdout_handler.addFilter(InfoFilter())
    logger.addHandler(stdout_handler)


class InfoFilter(logging.Filter):
    def filter(self, rec):
        return rec.levelno in (logging.DEBUG, logging.INFO)


class Whitelist(logging.Filter):
    def __init__(self, *whitelist):
        self.whitelist = [logging.Filter(name) for name in whitelist]

    def filter(self, record):
        return any([f.filter(record) for f in self.whitelist])
