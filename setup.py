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

# ----- overrides -----

# set these to anything but None to override the automatic defaults
packages = None
package_name = None
package_data = None
scripts = None
# ---------------------


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
from setuptools.command.install import install as _install
from setuptools.command.bdist_egg import bdist_egg as _bdist_egg

def get_requirement_files():
    import platform
    system_name = platform.system()
    requirements_path = os.path.join(
        os.path.abspath(os.path.dirname(__file__)), 'requirements'
    )
    files = glob.glob(
        os.path.join(requirements_path, 'requirements-[0-9].txt')
    )
    # Include all files of form requirements-<platform>-[0-9].txt,
    # where platform is {Windows, Linux, Darwin}
    files += glob.glob(
        os.path.join(
            requirements_path, 'requirements-%s-[0-9].txt' % system_name
        )
    )
    if len(files) == 0:
        raise Exception('Failed to find any requirements-[0-9].txt files')
    return sorted(files)


def read_requirement_file(filename):
    requirements = list()
    with open(filename, 'r') as f:
        for line in f:
            if line != '' and not line.startswith('#'):
                requirements.append(line.strip())
    return requirements


def pip_install_requirements():
    import pip
    for f in get_requirement_files():
        logger.info('install requirements in file: %s', f)
        requirements = read_requirement_file(f)
        for r in requirements:
            logger.info('install requirement "%s"', r)
            return_value = pip.main(['install', '--user', r])
            if return_value != 0:
                pip.main(['install', r])


class install(_install):

    def run(self):
        pip_install_requirements()
        _install.run(self)

    def do_egg_install(self):
        pip_install_requirements()
        _install.do_egg_install(self)


class bdist_egg(_bdist_egg):

    def run(self):
        pip_install_requirements()
        _bdist_egg.run(self)

    def do_egg_install(self):
        pip_install_requirements()
        _install.do_egg_install(self)


def find_scripts():
    return [s for s in setuptools.findall('bin/')
            if os.path.splitext(s)[1] != '.pyc']


def package_to_path(package):
    """
    Convert a package (as found by setuptools.find_packages)
    e.g. "foo.bar" to usable path
    e.g. "foo/bar"
    No idea if this works on windows
    """
    return package.replace('.', '/')


def find_subdirectories(package):
    """
    Get the subdirectories within a package
    This will include resources (non-submodules) and submodules
    """
    try:
        subdirectories = os.walk(package_to_path(package)).next()[1]
    except StopIteration:
        subdirectories = []
    return subdirectories


def subdir_findall(dir, subdir):
    """
    Find all files in a subdirectory and return paths relative to dir
    This is similar to (and uses) setuptools.findall
    However, the paths returned are in the form needed for package_data
    """
    strip_n = len(dir.split('/'))
    path = '/'.join((dir, subdir))
    return ['/'.join(s.split('/')[strip_n:]) for s in setuptools.findall(path)]


def find_package_data(packages):
    """
    For a list of packages, find the package_data
    This function scans the subdirectories of a package and considers all
    non-submodule subdirectories as resources, including them in
    the package_data
    Returns a dictionary suitable for setup(package_data=<result>)
    """
    package_data = {}
    for package in packages:
        package_data[package] = []
        for subdir in find_subdirectories(package):
            if '.'.join((package, subdir)) in packages:  # skip submodules
                logger.debug("skipping submodule %s/%s" % (package, subdir))
                continue
            if skip_tests and (subdir == 'tests'):  # skip tests
                logger.debug("skipping tests %s/%s" % (package, subdir))
                continue
            package_data[package] += subdir_findall(package_to_path(package),
                                                    subdir)
    return package_data


def readme():
    try:
        with open(os.path.join(os.path.dirname(__file__), 'README.md')) as f:
            return f.read()
    except (IOError, OSError):
        return ''


def get_version():
    src_path = os.path.join(
        os.path.abspath(os.path.dirname(__file__)),
        'src', 'python'
    )
    sys.path = [src_path] + sys.path
    import jtmodules
    return jtmodules.__version__


def get_requirements():
    files = get_requirement_files()
    requirements = list()
    for filename in files:
        requirements += read_requirement_file(filename)
    return requirements

# ----------- Override defaults here ----------------

scripts = []

packages = ['jtmodules']

package_data = {'': ['*.html', '*.svg', '*.js']}

if packages is None:
    packages = setuptools.find_packages('jtmodules')

if len(packages) == 0:
    raise Exception("No valid packages found")

if package_name is None:
    package_name = packages[0]

if package_data is None:
    package_data = find_package_data(packages)

if scripts is None:
    scripts = find_scripts()


setuptools.setup(
    name='jtmodules',
    version=get_version(),
    description='Jterator modules.',
    author='Markus D. Herrmann and Robin Hafen',
    author_email='markusdherrmann@gmail.com',
    url='https://github.com/tissuemaps/jtmodules',
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
    scripts=[],
    packages=packages,
    package_dir={'': 'src/python'},
    package_data={'': ['*.rst']},
    include_package_data=True,
    cmdclass={
        'install': install,
        'bdist_egg': bdist_egg
    },
    # install_requires=get_requirements()
)
