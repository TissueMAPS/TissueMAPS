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
    bin_path = os.path.join(
        os.path.abspath(os.path.dirname(__file__)), 'src', 'bin'
    )
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
        os.path.abspath(os.path.dirname(__file__)), 'src', 'tmserver'
    )
    sys.path = [src_path] + sys.path
    import version
    return version.__version__


setuptools.setup(
    name='tmserver',
    version=get_version(),
    description='TissueMAPS server. Web application for TissueMAPS.',
    author='Markus D. Herrmann and Robin Hafen',
    author_email='markusdherrmann@gmail.com',
    url='https://github.com/tissuemaps/tissuemaps',
    platforms=['Linux', 'OS-X'],
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
    packages=setuptools.find_packages('src'),
    package_dir={'': 'src'},
    include_package_data=True,
    install_requires=[
        'alembic==0.8.3',
        'cycler==0.9.0',
        'Flask==0.10.1',
        'Flask-JWT==0.3.1',
        'Flask-Migrate==1.6.0',
        'Flask-Script==2.0.5',
        'Flask-SQLAlchemy==2.1',
        'flask-sqlalchemy-session==1.1',
        'itsdangerous==0.24',
        'Jinja2==2.8',
        'Mako==1.0.3',
        'MarkupSafe==0.23',
        'numpy>=1.10.1',
        'pandas>=0.17.1',
        'passlib==1.6.5',
        'psycopg2==2.6.1',
        'PyJWT==1.4.0',
        'pyparsing==2.0.5',
        'python-dateutil==2.4.2',
        'python-editor==0.4',
        'pytz==2015.7',
        'scikit-learn>=0.16.1',
        'scipy>=0.16.1',
        'six==1.10.0',
        'sklearn==0.0',
        'SQLAlchemy>=1.0.9',
        'geoalchemy2==0.2.6',
        'Werkzeug==0.10.4',
        'wheel==0.24.0',
        'pytest==2.8.2',
        'flask-redis==0.1.0',
        'py4j>=0.10.1',
        'Flask-uWSGI-WebSocket>=0.5.2',
        'gevent>=1.1.1',
        'shapely>=1.5.15',
    ],
    dependency_links=[
        'git+https://github.com/dtheodor/flask-sqlalchemy-session/master#egg=flask_sqlalchemy_session',
    ]
)

