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


def find_data_files():
    elasticluster_path = os.path.join(
        os.path.abspath(os.path.dirname(__file__)), 'elasticluster'
    )
    elasticluster_playbooks_path = os.path.join(
        elasticluster_path, 'elasticluster', 'share', 'playbooks'
    )
    root_path = os.path.join('tmsetup', 'share', 'playbooks', 'elasticluster')
    files = list()
    for d, _, f in os.walk(elasticluster_playbooks_path):
        path = os.path.relpath(d, elasticluster_playbooks_path)
        files.append((os.path.join(root_path, path), os.path.join(d, f)))
    return files


def get_version():
    logger.info('get package version')
    src_path = os.path.join(
        os.path.abspath(os.path.dirname(__file__)), 'tmsetup'
    )
    sys.path = [src_path] + sys.path
    import version
    return version.__version__


setuptools.setup(
    name='tmsetup',
    version=get_version(),
    description='TissueMAPS setup and deployment in virtual environments.',
    author='Markus D. Herrmann',
    author_email='markusdherrmann@gmail.com',
    url='https://github.com/tissuemaps/tmsetup',
    license='GPL-3.0+',
    platforms=['Linux', 'OS-X'],
    classifiers=[
        'Intended Audience :: Developers',
        'Intended Audience :: Science/Research',
        'Intended Audience :: System Administrators',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Development Status :: 4 - Beta',
        'Operating System :: POSIX :: Linux',
        'Operating System :: POSIX :: Other',
        'Operating System :: MacOS',
        'Environment :: Console',
        'Topic :: System :: Clustering',
        'Topic :: Scientific/Engineering',
        'Topic :: System :: Distributed Computing',
    ],
    scripts=find_scripts(),
    packages=setuptools.find_packages(),
    include_package_data=True,
    data_files=find_data_files(),
    install_requires=[
       'ansible>=2.2.1',
       'container>=0.3.0',
       'apache-libcloud>=1.3.0',
       'boto3>=1.4.1',
       'docker-py>=1.10.6',
       'docker-compose>=1.9',
       'PyYAML>=3.11',
       'psycopg2>=2.6.1',
       # Docker compose requires a specific version of requests. Hereby, we
       # ensure that it gets correctly installed.
       'requests >= 2.6.1, != 2.11.0, < 2.12',
       'shade>=1.12.1',
       'whichcraft>=0.4.0'
    ]
)

