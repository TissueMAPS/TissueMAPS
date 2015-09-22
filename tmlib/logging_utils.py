import logging


VERBOSITY_LEVELS = {
    0: None,  # Equivalent to no logging.
    1: logging.WARN,  # For simplicity. Includes ERROR, CRITICAL
    2: logging.INFO,
    3: logging.DEBUG,
    4: logging.NOTSET,  # Equivalent to no filtering. Everything is logged.
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


class Whitelist(logging.Filter):
    def __init__(self, *whitelist):
        self.whitelist = [logging.Filter(name) for name in whitelist]

    def filter(self, record):
        return any(f.filter(record) for f in self.whitelist)
