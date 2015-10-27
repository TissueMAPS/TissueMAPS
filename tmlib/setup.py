#! /usr/bin/env python
# encoding: utf-8

import os
import sys
from setuptools import setup, find_packages


def get_version():
    src_path = os.path.abspath(__file__)
    sys.path.append(src_path)
    import tmlib
    return tmlib.__version__


setup(
    name='tmlib',
    version=get_version(),
    description='TissueMAPS library',
    long_description='Python package for image processing tasks required by TissueMAPS',
    author='Markus D. Herrmann and Robin Hafen',
    author_email='markusdherrmann at gmail dot com',
    url='https://github.com/TissueMAPS/tissuemapslibrary',
    license='GPL',
    platforms=['Linux', 'OS-X'],
    classifiers=[
        'Topic :: Scientific/Engineering :: Image Recognition',
        'Topic :: Scientific/Engineering :: Information Analysis',
        'Topic :: System :: Emulators',
        'Intended Audience :: Developers',
        'Intended Audience :: Science/Research',
        'Intended Audience :: System Administrators',
        'Programming Language :: Python',
        'Development Status :: 4 - Beta',
        'Operating System :: POSIX :: Linux',
        'Operating System :: MacOS',
        'Natural Language :: English'
    ],
    scripts=['tmlib'],
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
    ]
)
