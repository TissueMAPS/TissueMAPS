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
    sys_name = platform.system()
    requirements_path = os.path.join(
        os.path.abspath(os.path.dirname(__file__)), 'requirements'
    )
    files = glob.glob(
        os.path.join(requirements_path, 'requirements-[0-9].txt')
    )
    # Include all files of form requirements-<platform>-[0-9].txt,
    # where platform is {Windows, Linux, Darwin}
    files += glob.glob(
        os.path.join(requirements_path, 'requirements-%s-[0-9].txt' % sys_name)
    )
    files += glob.glob(
        os.path.join(requirements_path, 'requirements-git.txt')
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
            args_list = ['install']
            if '--user' in sys.argv:
                args_list.append('--user')
            if '-e' in sys.argv or '--editable' in sys.argv:
                args_list.append('-e')
            args_list.append(r)
            pip.main(args_list)


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
    bin_path = os.path.join(
        os.path.abspath(os.path.dirname(__file__)), 'src', 'python', 'bin'
    )
    scripts = list()
    for f in os.listdir(bin_path):
        if not f.endswith('pyc'):
            script_path = os.path.relpath(
                os.path.join(bin_path, f),
                os.path.abspath(os.path.dirname(__file__))
            )
            scripts.append(script_path)
    return scripts


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
                logging.debug("skipping submodule %s/%s" % (package, subdir))
                continue
            if skip_tests and (subdir == 'tests'):  # skip tests
                logging.debug("skipping tests %s/%s" % (package, subdir))
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
    import tmclient
    return tmclient.__version__


def get_requirements():
    requirements = list()
    for f in get_requirement_files():
        logger.info('install requirements in file: %s', f)
        requirements += read_requirement_file(f)
    return requirements

# ----------- Override defaults here ----------------

package_data = {'': ['*.html', '*.svg', '*.js']}

if packages is None:
    packages = setuptools.find_packages(os.path.join('src', 'python'))

if len(packages) == 0:
    raise Exception("No valid packages found")

if package_name is None:
    package_name = packages[0]

if package_data is None:
    package_data = find_package_data(packages)


setuptools.setup(
    name='tmclient',
    version=get_version(),
    description='Client library for TissueMAPS RESTful API.',
    author='Markus D. Herrmann and Robin Hafen',
    author_email='markusdherrmann@gmail.com',
    url='https://github.com/tissuemaps/tmclient',
    platforms=['Linux', 'OS-X'],
    classifiers=[
        'Topic :: Scientific/Engineering :: Information Analysis',
        'Topic :: System :: Emulators',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'Programming Language :: Python',
        'Development Status :: 4 - Beta',
        'Operating System :: POSIX :: Linux',
        'Operating System :: MacOS'
    ],
    scripts=find_scripts(),
    packages=packages,
    package_dir={'': 'src/python'},
    package_data={'': ['*.rst']},
    cmdclass={
        'install': install,
        'bdist_egg': bdist_egg
    },
    include_package_data=True,
    # install_requires=get_requirements()
)

