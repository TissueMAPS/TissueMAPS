import logging
import sys

import model
import user
import experiment
import appstate
import mapobject
import tool
import serialize

def configure_logging(name):
    fmt = '%(asctime)s | %(levelname)-8s | %(name)-40s | %(message)s'
    datefmt = '%Y-%m-%d %H:%M:%S'
    formatter = logging.Formatter(fmt=fmt, datefmt=datefmt)

    log = logging.getLogger(name)
    log.setLevel(logging.INFO)

    stderr_handler = logging.StreamHandler(stream=sys.stderr)
    stderr_handler.name = 'err'
    stderr_handler.setFormatter(formatter)
    stderr_handler.setLevel(logging.WARN)
    log.addHandler(stderr_handler)

    stdout_handler = logging.StreamHandler(stream=sys.stdout)
    stdout_handler.name = 'out'
    stdout_handler.setFormatter(formatter)
    log.addHandler(stdout_handler)


log = configure_logging(__name__)
