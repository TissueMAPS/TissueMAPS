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


def get_version():
    src_path = join(dirname(abspath(__file__)),
                    'src', 'jtlib', '__init__.py')
    ctx = {}
    execfile(src_path, ctx, ctx)
    return ctx['__version__']


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
    package_dir={'': 'src'},
    include_package_data=True,
    install_requires=[
        'numpy>=1.12.0',
        'pandas>=0.19.2',
        'scipy>=0.16.0',
        'cached-property>=1.3.0',
        'cython>=0.24',
        'opencv-contrib-python>=3.2',
        'scikit-image>=0.11.3',
        'mahotas>=1.4.0',
        'centrosome>=1.0.5',
        'colorlover>=0.2.1',
        'plotly>=2.0.0',
        'pyasn1>=0.1.9',
        'pytest>=2.8.2',
        'ndg-httpsclient>=0.4.0',
        'sep>=1.0.0',
        'simpleitk>=1.0.0'
    ],
    # `centrosome` and `scipy` require that `Cython` and `numpy`
    # (resp.) are already set up and available during installation
    setup_requires=[
        'numpy>=1.12.0',
        'cython>=0.24'
    ]
)
