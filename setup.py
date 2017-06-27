#!/usr/bin/env python
# -*- coding: utf-8 -*-
''' distribute- and pip-enabled setup.py '''
from __future__ import print_function
import os
from os.path import abspath, dirname, join, splitext
import re
import sys
import glob
import logging
import shutil

logger = logging.getLogger(__name__)

# ----- control flags -----

# fallback to setuptools if distribute isn't found
setup_tools_fallback = True

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

def get_version():
    sys.path.insert(0, abspath(dirname(__file__)))
    import jtlib
    return jtlib.__version__

setuptools.setup(
    name='jtlibrary',
    version=get_version(),
    description='Jterator library.',
    author='Markus D. Herrmann',
    url='https://github.com/tissuemaps/jtlibrary',
    platforms=['Linux', 'MacOS'],
    classifiers=[
        'Topic :: Scientific/Engineering :: Image Recognition',
        'Topic :: Scientific/Engineering :: Information Analysis',
        'Topic :: System :: Emulators',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'Programming Language :: Python',
        'Development Status :: 4 - Beta',
        'Operating System :: POSIX :: Linux',
        'Operating System :: MacOS'
    ],
    scripts=[],
    packages=['jtlib'],
    include_package_data=True,  # include files mentioned by MANIFEST.in
    install_requires=[
        'numpy>=1.12.0',
        'pandas>=0.19.2',
        'scipy>=0.16.0',
        'cython>=0.24',
        'opencv-contrib-python>=3.2',
        'scikit-image>=0.11.3',
        'mahotas>=1.4.0',
        'centrosome>=1.0.5',
        'colorlover>=0.2.1',
        'plotly>=2.0.0',
        'pyasn1>=0.1.9',
        'ndg-httpsclient>=0.4.0',
    ]
)
