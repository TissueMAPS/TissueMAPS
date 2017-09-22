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

def find_scripts():
    return [s for s in setuptools.findall('bin/')
            if os.path.splitext(s)[1] != '.pyc']

def get_version():
    src_path = os.path.join(
        os.path.abspath(os.path.dirname(__file__)),
        'src', 'python'
    )
    sys.path = [src_path] + sys.path
    import jtmodules
    return jtmodules.__version__


setuptools.setup(
    name='jtmodules',
    version=get_version(),
    description='Jterator modules.',
    author='Markus D. Herrmann',
    url='https://github.com/tissuemaps/jtmodules',
    license='Apache-2.0',
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
    packages = ('jtmodules', ),
    package_dir={'': 'src/python'},
    include_package_data=True,
    install_requires=[
        'numpy>=1.10.1',
        'cython>=0.24',
        'centrosome>=1.0.5',
        'scikit-image>=0.11.3',
        'mahotas>=1.4.0',
        'opencv-contrib-python>=3.2',
        'pytest>=2.8.2',
        'scipy>=0.16.0',
        'jtlibrary>=0.2.0'
    ]
)
