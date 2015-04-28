#! /usr/bin/env python
# encoding: utf-8

import os
import sys
from setuptools import setup


def readme():
    try:
        with open(os.path.join(os.path.dirname(__file__), 'README.md')) as f:
            return f.read()
    except (IOError, OSError):
        return ''


def get_version():
    src_path = os.path.abspath(__file__)
    sys.path.append(src_path)
    import illuminati
    return illuminati.__version__


setup(
    name='illuminati',
    version=get_version(),
    description='Command line tool for preprocessing and generation of '
                'image pyramids in "zoomify" format.',
    author='Markus Herrmann and Robin Hafen',
    author_email='markusdherrmann at gmail dot com',
    url='https://github.com/pelkmanslab/illuminati',
    license='MIT',
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
    scripts=['illuminati'],
    packages=['illuminati'],
    package_dir={''},
    package_data={},
    include_package_data=True,
    download_url='https://github.com/pelkmanslab/illuminati/tarball/master',
    install_requires=[
        'numpy>=1.9.2',
        'scipy>=0.15.1',
        'scikit-image>=0.11.2',
        'PyYAML>=3.11',
        'jsonschema>=2.4.0',
        'h5py>=2.4.0',
        'pygobject>=3.14.0',
        'argparse',
        'Shapely>=1.5.7'
    ]
    # tests_require=['nose>=1.0'],
    # test_suite='nose.collector',
)
