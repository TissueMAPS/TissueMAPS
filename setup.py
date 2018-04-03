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


def get_cli_tools():
    src_path = os.path.abspath(os.path.dirname(__file__))
    root = os.path.join(src_path, 'tmlib', 'workflow')
    def _is_step(d):
        # A step is defined as a subpackage that implements the following
        # modules: api, cli, args
        d = os.path.join(root, d)
        return(
            os.path.isdir(d) and
            glob.glob(os.path.join(d, '__init__.py')) and
            glob.glob(os.path.join(d, 'api.py')) and
            glob.glob(os.path.join(d, 'cli.py')) and
            glob.glob(os.path.join(d, 'args.py'))
        )

    return filter(_is_step, os.listdir(root))


def build_console_scripts():
    names = get_cli_tools()
    cli_tools = list()
    for name in names:
        cli_tools.append(
            '{name} = tmlib.workflow.{name}.cli:{cls}.__main__'.format(
                name=name, cls=name.capitalize()
            )
        )
    # NOTE: Spark entry points must have .py ending, otherwise they will
    # be interpreted as scala files.
    cli_tools.extend([
        'tm_workflow = tmlib.workflow.manager:WorkflowManager.__main__',
        'tm_tool = tmlib.tools.manager:ToolRequestManager.__main__',
    ])
    return cli_tools


def get_version():
    src_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'tmlib')
    sys.path = [src_path] + sys.path
    import version
    return version.__version__


setuptools.setup(
    name='tmlibrary',
    version=get_version(),
    description='TissueMAPS library for distibuted image analysis routines.',
    author='Markus D. Herrmann',
    url='https://github.com/tissuemaps/tmlibrary',
    license='AGPL-3.0+',
    platforms=['Linux', 'MacOS'],
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
       # It may need to be installed beforehand.
       'numpy>=1.12.0',
       'scipy>=0.16.0',
       'cached-property>=1.3.0',
       'decorator>=3.4.2',
       'FITS-tools',
       'geoalchemy2>=0.3.0',
       'h5py>=2.5.0',
       'image-registration==0.2.1',
       'jtlibrary>=0.3.2',
       'mahotas>=1.4.1',
       'matplotlib>=2.0.0',
       'mock>=1.0.1',
       'natsort>=4.0.3',
       'nose>=1.3.7',
       'opencv-contrib-python>=3.2',
       'openslide-python>=1.1.0',
       'pandas>=0.19.2',
       'passlib>=1.6.5',
       'paramiko>=1.15.3',
       'parsedatetime>=1.5',
       'prettytable>=0.7.2',
       'pyparsing>=2.0.3',
       'pypng>=0.0.17',
       # Python-bioformats installs javabridge, which requires Java
       # Ubuntu 14.04:
       #    sudo apt-get -y install openjdk-7-jdk
       # Ubuntu 16.04:
       #    sudo apt-get -y install openjdk-8-jdk
       'python-bioformats>=1.0.9',
       'python-dateutil>=2.4.2',
       'pytest>=3.0.7',
       'pytz>=2015.7',
       'PyYAML>=3.11',
       'scikit-image>=0.12.0',
       'scikit-learn>=0.18',
       # Ubuntu:
       #    sudo apt-get -y install libgeos-dev
       'shapely>=1.5.15',
       'simplejson>=3.10',
       'sqlalchemy>=1.1.5',
       'sqlalchemy-utils>=0.32.9',
       # Ubuntu:
       #    sudo apt-get -y install libpq-dev
       'psycopg2>=2.7',
       'tables>=3.2.2',
       'ruamel.yaml>=0.10.11',
       # Ubuntu:
       #    sudo apt-get -y install libxml2-dev libxslt1-dev zlib1g-dev
       'lxml',
       'whichcraft>=0.4.0',
       'gc3pie==2.5.dev',
    ],
    extras_require = {
       'jterator_r_modules': [
           'rpy2>=2.7.4' # Requires R
        ],
       'jterator_matlab_modules': [
           'matlab-wrapper>=0.9.6', # Requires Matlab
        ]
    },
    dependency_links=[
        # The dependency_links functionality has been deprecated, but it can
        # be activaeted via --process-dependency-links
        'https://github.com/tissuemaps/gc3pie/tarball/master#egg=gc3pie-2.5.dev',
        # 'https://github.com/tissuemaps/sqlalchemy-utils/tarball/master#egg=sqlalchemy_utils'
    ]
)
