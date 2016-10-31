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


def build_console_scripts():
    src_path = os.path.abspath(os.path.dirname(__file__))
    sys.path = [src_path] + sys.path
    import tmlib
    names = tmlib.get_cli_tools()
    cli_tools = list()
    for name in names:
        cli_tools.append(
            '{name} = tmlib.workflow.{name}.cli:{cls}.main'.format(
                name=name, cls=name.capitalize()
            )
        )
    cli_tools.append(
        'tm_workflow = tmlib.workflow.manager:WorkflowManager.main'
    )
    return cli_tools


def get_version():
    src_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'tmlib')
    sys.path = [src_path] + sys.path
    import version
    return version.__version__


setuptools.setup(
    name='tmlibrary',
    version=get_version(),
    description='TissueMAPS library for distibuted image processing routines.',
    author='Markus D. Herrmann',
    author_email='markusdherrmann@gmail.com',
    url='https://github.com/tissuemaps/tmlibrary',
    license='AGPL-3.0+',
    platforms=['Linux', 'OS-X'],
    classifiers=[
        'Environment :: Console',
        'Environment :: Web Environment',
        'Topic :: Scientific/Engineering :: Image Recognition',
        'Topic :: Scientific/Engineering :: Information Analysis',
        'Topic :: System :: Emulators',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'Intended Audience :: Science/Research',
        'Programming Language :: Python',
        'Development Status :: 4 - Beta',
        'Operating System :: POSIX :: Linux',
        'Operating System :: MacOS :: MacOS X'
    ],
    scripts=find_scripts(),
    entry_points={'console_scripts': build_console_scripts()},
    packages=setuptools.find_packages(),
    include_package_data=True,
    install_requires=[
       'Cython>=0.22.1',
       # Some packages try to import Numpy in the setup.py.
       # It may have to be installed first: pip install numpy
       'numpy>=1.10.1',
       'scipy>=0.16.0',
       'cached-property>=1.3.0',
       'decorator==3.4.2',
       'FITS-tools',
       'geoalchemy2>=0.3.0',
       'h5py>=2.5.0',
       'image-registration==0.2.1',
       'mahotas>=1.4.1',
       'matlab-wrapper>=0.9.6',
       'mock>=1.0.1',
       'natsort>=4.0.3',
       'nose>=1.3.7',
       'openslide-python>=1.1.0',
       'pandas>=0.17.1',
       'passlib>=1.6.5',
       'paramiko==1.15.3',
       'parsedatetime>=1.5',
       'prettytable>=0.7.2',
       'pyparsing>=2.0.3',
       'pypng>=0.0.17',
       # Python-bioformats installs javabridge, which requires Java
       # Ubuntu:
       # sudo apt-get -y install openjdk-7-jdk
       # export JAVA_HOME=/usr/lib/jvm/java-1.7.0-openjdk-amd64
       'python-bioformats>=1.0.9',
       'python-dateutil>=2.4.2',
       'pytest>=2.9.1',
       'pytz>=2015.7',
       'PyYAML>=3.11',
       'scikit-image>=0.12.0',
       'scikit-learn>=0.18',
       # Ubuntu: sudo apt-get -y install libgeos-dev
       'shapely>=1.5.15',
       'sqlalchemy>=0.9',
       'sqlalchemy-utils>=0.32.9',
       'tables>=3.2.2',
       'ruamel.yaml>=0.10.11'
       'pyfakefs',
       'gc3pie==2.5.dev',
       'APScheduler>=3.0.5',
       # Ubuntu: sudo apt-get -y install libxml2-dev libxslt1-dev zlib1g-dev
       'lxml',
       # 'rpy2>=2.7.4'
    ],
    dependency_links=[
        # The dependency_links functionality has been deprecated, but it can
        # be activaeted via --process-dependency-links
        'https://github.com/jmcgeheeiv/pyfakefs/tarball/master#egg=pyfakefs',
        'https://github.com/tissuemaps/gc3pie/tarball/master#egg=gc3pie-2.5.dev',
        # 'https://github.com/tissuemaps/sqlalchemy-utils/tarball/master#egg=sqlalchemy_utils'
        # TODO: include TissueMAPS repos once they are public
    ],
)
