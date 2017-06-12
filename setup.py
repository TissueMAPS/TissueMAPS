#!/usr/bin/env python
# -*- coding: utf-8 -*-
''' distribute- and pip-enabled setup.py '''
from __future__ import print_function
import os
import sys
import logging

logger = logging.getLogger(__name__)


# ----- control flags -----

# fallback to setuptools if distribute isn't found
setup_tools_fallback = True

# don't include subdir named 'tests' in package_data
skip_tests = False

# print some extra debugging info
debug = True

# -------------------------

if debug:
    logging.basicConfig(level=logging.DEBUG)
else:
    logging.basicConfig(level=logging.INFO)

# distribute import and testing
try:
    import distribute_setup
    distribute_setup.use_setuptools()
    logger.info('distribute_setup.py imported and used')
except ImportError:
<<<<<<< HEAD
    # falback to setuptools?
    # distribute_setup.py was not in this directory
    if not (setup_tools_fallback):
        import setuptools
        if not (hasattr(setuptools, '_distribute')
                and setuptools._distribute):
            raise ImportError('distribute was not found and fallback to '
                              'setuptools was not allowed')
        else:
            logger.debug('distribute_setup.py not found, defaulted to '
                          'system distribute')
    else:
        logger.debug('distribute_setup.py not found, defaulting to system '
                      'setuptools')


import setuptools

def find_scripts():
    bin_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'bin')
    scripts = list()
    for f in os.listdir(bin_path):
        if not f.endswith('pyc'):
            script_path = os.path.relpath(
                os.path.join(bin_path, f),
                os.path.abspath(os.path.dirname(__file__))
            )
            scripts.append(script_path)
    return scripts


def get_version():
    logger.info('get package version')
    src_path = os.path.join(
        os.path.abspath(os.path.dirname(__file__)), 'tmdeploy'
    )
    sys.path = [src_path] + sys.path
    import version
    return version.__version__


setuptools.setup(
    name='tmdeploy',
    version=get_version(),
    description='TissueMAPS deployment in virtual environments.',
    url='https://github.com/tissuemaps/tmdeploy',
    author='Markus D. Herrmann',
    license='GPL-3.0+',
    platforms=['Linux', 'MacOSX'],
)

