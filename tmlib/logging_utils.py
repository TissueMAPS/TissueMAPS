import sys
import logging


VERBOSITY_LEVELS = {
    0: logging.WARN,  # For simplicity. Includes ERROR, CRITICAL
    1: logging.INFO,
    2: logging.DEBUG,
    3: logging.NOTSET,  # Equivalent to no filtering. Everything is logged.
}
LOGGING_LEVELS = {
    'NONE': None,
    'CRITICAL': logging.CRITICAL,
    'ERROR': logging.ERROR,
    'WARN': logging.WARN,
    'INFO': logging.INFO,
    'DEBUG': logging.DEBUG,
    'NOTSET': logging.NOTSET,
}
VERBOSITY_TO_LEVELS = {
    0: 'NONE',
    1: 'WARN',
    2: 'INFO',
    3: 'DEBUG',
    4: 'NOTSET',
}


def map_log_verbosity(verbosity):
    '''
    Parameters
    ----------
    verbosity: int
        logging verbosity level (0-4)

    Returns
    -------
    Returns a logging level as exported by `logging` module.
    By default returns logging.NOTSET
    '''
    if verbosity > len(VERBOSITY_LEVELS):
        verbosity = len(VERBOSITY_LEVELS) - 1
    return VERBOSITY_LEVELS.get(verbosity, logging.NOTSET)


def configure_logging(name, verbosity):

    fmt = '%(asctime)s %(name)-40s %(levelname)-8s %(message)s'
    datefmt = '%Y-%m-%d %H:%M:%S'
    formatter = logging.Formatter(fmt=fmt, datefmt=datefmt)

    logger = logging.getLogger(name)
    logger.setLevel(map_log_verbosity(verbosity))

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
    return logger


class InfoFilter(logging.Filter):
    def filter(self, rec):
        return rec.levelno in (logging.DEBUG, logging.INFO)


class Whitelist(logging.Filter):
    def __init__(self, *whitelist):
        self.whitelist = [logging.Filter(name) for name in whitelist]

    def filter(self, record):
        return any([f.filter(record) for f in self.whitelist])
