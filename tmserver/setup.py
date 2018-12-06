#!/usr/bin/env python
# -*- coding: utf-8 -*-
''' distribute- and pip-enabled setup.py '''
from __future__ import print_function
import os
import re
import sys
import glob
import logging
import shutil

logger = logging.getLogger(__name__)

# fallback to setuptools if distribute isn't found
setup_tools_fallback = True

# print some extra debugging info
debug = True


if debug:
    logging.basicConfig(level=logging.DEBUG)
else:
    logging.basicConfig(level=logging.INFO)

# distribute import and testing
try:
    import distribute_setup
    distribute_setup.use_setuptools()
    logger.info("distribute_setup.py imported and used")
except ImportError:
    # falback to setuptools?
    # distribute_setup.py was not in this directory
    if not (setup_tools_fallback):
        import setuptools
        if not (hasattr(setuptools, '_distribute')
                and setuptools._distribute):
            raise ImportError("distribute was not found and fallback to "
                              "setuptools was not allowed")
        else:
            logger.debug("distribute_setup.py not found, defaulted to "
                          "system distribute")
    else:
        logger.debug("distribute_setup.py not found, defaulting to system "
                      "setuptools")


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
    src_path = os.path.join(
        os.path.abspath(os.path.dirname(__file__)), 'tmserver'
    )
    sys.path = [src_path] + sys.path
    import version
    return version.__version__


setuptools.setup(
    name='tmserver',
    version=get_version(),
    description='TissueMAPS server application.',
    author='Markus D. Herrmann and Robin Hafen',
    author_email='markusdherrmann@gmail.com',
    url='https://github.com/tissuemaps/tissuemaps',
    platforms=['Linux', 'OS-X'],
    license='AGPL-3.0+',
    classifiers=[
        'Environment :: Web Environment',
        'Topic :: System :: Emulators',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'Intended Audience :: Science/Research',
        'Programming Language :: Python',
        'Development Status :: 4 - Beta',
        'Operating System :: POSIX :: Linux',
        'Operating System :: MacOS'
    ],
    scripts=find_scripts(),
    packages=setuptools.find_packages(),
    include_package_data=True,
    install_requires=[
        'alembic>=0.8.3',
        'apscheduler>=3.3.1',
        'Flask>=0.10.1',
        'Flask-JWT>=0.3.1',
        'Flask-Migrate>=1.6.0',
        'Flask-Script>=2.0.5',
        'Flask-SQLAlchemy>=2.1',
        'flask-sqlalchemy-session>=1.1',
        'flask-redis>=0.1.0',
        'Flask-uWSGI-WebSocket>=0.5.2',
        'Werkzeug>=0.10.4',
        'gc3pie>=2.5.1',
        'gevent>=1.1.1',
        'itsdangerous>=0.24',
        'Jinja2>=2.8',
        'Mako>=1.0.3',
        'MarkupSafe>=0.23',
        'PyJWT>=1.4.0',
        'pyparsing>=2.0.5',
        'python-dateutil>=2.4.2',
        'python-editor>=0.4',
        'tmlibrary>=0.1.0'
    ]
)
