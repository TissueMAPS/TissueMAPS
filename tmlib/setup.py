#! /usr/bin/env python
# encoding: utf-8

import os
import sys
from setuptools import setup, find_packages


def get_version():
    src_path = os.path.abspath(__file__)
    sys.path.append(src_path)
    import tmt
    return tmt.__version__


setup(
    name='tmt',
    version=get_version(),
    description='TissueMAPS toolbox. Image processing and data analysis '
                'routines for TissueMAPS.',
    author='Markus D. Herrmann and Robin Hafen',
    author_email='markusdherrmann at gmail dot com',
    url='https://github.com/hackermd/tissuemapstoolbox',
    platforms=['Linux', 'OS-X'],
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
    scripts=['tmt'],
    packages=find_packages(),
    package_dir={''},
    package_data={'': ['*.rst']},
    include_package_data=True,
    install_requires=[
        'docutils>=0.3',
        'numpy>=1.9.2',
        'natsort>=3.5.6',
        'mahotas>=1.3.0',
        'image-registration>=0.2.1',
        'pandas>=0.16.2',
        'scipy>=0.15.1',
        'scikit-image>=0.11.2',
        'scikit-learn>=0.16.0',
        'PyYAML>=3.11',
        'jsonschema>=2.4.0',
        'h5py>=2.4.0',
        'pygobject>=3.14.0',
        'argparse',
        'Shapely>=1.5.7',
        'subprocess32>=3.2.6'
    ]
)
