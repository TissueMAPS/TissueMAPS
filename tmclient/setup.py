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


setuptools.setup(
    name='tmclient',
    version='0.5.0',  # use bumpversion to advance
    description='RESTful API client for TissueMAPS.',
    author='Markus D. Herrmann',
    license='Apache-2.0',
    url='https://github.com/tissuemaps/tmclient',
    platforms=['Linux', 'MacOS', 'Windows'],
    classifiers=[
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: MacOS',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: POSIX :: Linux',
        'Intended Audience :: Science/Research',
        'Topic :: Scientific/Engineering :: Information Analysis',
        'Topic :: Scientific/Engineering :: Bio-Informatics',
        'Topic :: Internet :: WWW/HTTP',
        'Programming Language :: Python :: 2',
        'Development Status :: 4 - Beta'
    ],
    entry_points={
        'console_scripts': [
            'tm_client = tmclient.api:TmClient.__main__',
        ]
    },
    packages=setuptools.find_packages(os.path.join('src', 'python')),
    package_dir={'': os.path.join('src', 'python')},
    package_data={'': ['*.rst']},
    include_package_data=True,
    install_requires=[
        'matplotlib',
        'opencv-contrib-python>=3.2',
        'pandas>=0.19.1',
        'prettytable>=0.7.2',
        'PyYAML>=3.11',
        'requests>=2.11.0',
        'scikit-image',
        'seaborn',
    ]
)
