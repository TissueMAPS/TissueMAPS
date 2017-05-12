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
    classifiers=[
        'Intended Audience :: Developers',
        'Intended Audience :: Science/Research',
        'Intended Audience :: System Administrators',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Unix Shell',
        'Development Status :: 4 - Beta',
        'Operating System :: POSIX :: Linux',
        'Operating System :: MacOS',
        'Environment :: Console',
        'Topic :: Scientific/Engineering',
        'Topic :: System :: Clustering',
        'Topic :: System :: Distributed Computing',
        'Topic :: System :: Software Distribution',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)'
    ],
    scripts=find_scripts(),
    packages=setuptools.find_packages(),
    include_package_data=True,
    install_requires=[
       'ansible>=2.2.1',
       'ansible-container>=0.3.0,<=0.4',
       'apache-libcloud>=1.3.0',
       'boto3>=1.4.1',
       'docker-py>=1.10.6',
       # Ansible container requires a specific version of Docker compose.
       'docker-compose==1.9.0',
       'PyYAML>=3.11',
       'psycopg2>=2.6.1',
       # Ansible container requires a specific version of requests.
       'requests==2.11.1',
       'shade>=1.12.1',
       'whichcraft>=0.4.0',
       # OpenStack's `osc-lib` has stricter requirements that are not picked up
       # because of pip's issue #988.  The only workaround for now is to manually
       # add the complete requirement expression as a top-level dependency
       'Babel>=2.3.4,!=2.4.0',
    ]
)

