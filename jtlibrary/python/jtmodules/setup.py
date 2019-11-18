#!/usr/bin/env python
# -*- coding: utf-8 -*-
''' distribute- and pip-enabled setup.py '''
from __future__ import print_function
import os
import re
import sys
import glob
import shutil

from os.path import abspath, dirname, join, splitext


import setuptools


setuptools.setup(
    name='jtmodules',
    version='0.5.0',  # use bumpversion to advance
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
    packages = ['jtmodules'],
    package_dir={'': 'src'},
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
    ],
    # `centrosome` and `scipy` require that `Cython` and `numpy`
    # (resp.) are already set up and available during installation
    setup_requires=[
        'numpy>=1.12.0',
        'cython>=0.24'
    ]
)
