# -*- coding: utf-8 -*-
import six
import os
import glob
import yaml
import requests
import traceback
import subprocess
import pytest
import pandas as pd
from natsort import natsorted
from yaml import Loader, SafeLoader

from tmclient.api import TmClient
from tmclient.errors import ResourceError


def _construct_yaml_str(self, node):
    # Override default string handling function to always return unicode
    return self.construct_scalar(node)

Loader.add_constructor(u'tag:yaml.org,2002:str', _construct_yaml_str)
SafeLoader.add_constructor(u'tag:yaml.org,2002:str', _construct_yaml_str)


class Expectations(object):

    def __init__(self, description):
        required_keys = {
            'n_channels', 'n_mapobject_types', 'n_cycles', 'n_wells', 'n_sites',
            'well_dimensions'
        }
        for k in required_keys:
            if k not in description:
                raise KeyError('Key "{0}" is required in expectations file.')
            setattr(self, k, description[k])


class Settings(object):

    def __init__(self, description):
        required_keys = {
            'workflow_timeout'
        }
        for k in required_keys:
            if k not in description:
                raise KeyError('Key "{0}" is required in settings file.')
            setattr(self, k, description[k])


class ExperimentInfo(object):

    def __init__(self, directory):
        self.directory = os.path.expanduser(os.path.expandvars(directory))
        self.name = os.path.basename(self.directory)
        plates_dir = os.path.join(self.directory, 'plates')
        if not os.path.exists(plates_dir):
            raise OSError(
                'Plates directory does not exist: {0}'.format(plates_dir)
            )
        self.plates = glob.glob(os.path.join(plates_dir, '*'))
        description = self._load_experiment_description()
        required_keys = {
            'microscope_type', 'workflow_type', 'plate_format',
            'plate_acquisition_mode'
        }
        for key in required_keys:
            if key not in description:
                raise KeyError(
                    'Experiment description requires key "{0}"'.format(key)
                )
            setattr(self, key, description[key])

    @staticmethod
    def _load_yaml(filename):
        if not os.path.exists(filename):
            raise OSError('YAML file does not exist: {0}'.format(filename))
        with open(filename) as f:
            return yaml.safe_load(f)

    @staticmethod
    def _load_csv(filename):
        if not os.path.exists(filename):
            raise OSError('CSV file does not exist: {0}'.format(filename))
        return pd.read_csv(filename)

    def get_expected_feature_values(self, mapobject_type):
        return self._load_csv(self._get_feature_values_file(mapobject_type))

    def get_expected_metadata(self, mapobject_type):
        return self._load_csv(self._get_metadata_file(mapobject_type))

    @property
    def expectations(self):
        filename = os.path.join(self.directory, 'expectations.yaml')
        return Expectations(self._load_yaml(filename))

    @property
    def settings(self):
        filename = os.path.join(self.directory, 'settings.yaml')
        return Settings(self._load_yaml(filename))

    def _get_feature_values_file(self, mapobject_type):
        return os.path.join(
            self.directory, 'feature-values_{0}.csv'.format(mapobject_type)
        )

    def _get_metadata_file(self, mapobject_type):
        return os.path.join(
            self.directory, 'metadata_{0}.csv'.format(mapobject_type)
        )

    def _load_experiment_description(self):
        filename = os.path.join(self.directory, 'experiment_description.yaml')
        return self._load_yaml(filename)

    @property
    def workflow_description(self):
        return self._load_yaml(self.workflow_description_file)

    @property
    def workflow_description_file(self):
        description_file = os.path.join(
            self.directory, 'workflow_description.yaml'
        )
        if not os.path.exists(description_file):
            raise OSError(
                'Workflow description file does not exist: {0}'.format(
                    description_file
                )
            )
        return description_file

    @property
    def jterator_project(self):
        pipeline_description = self._load_yaml(self._jterator_pipeline_file)
        handles_descriptions = dict()
        for name, handles_file in self._jterator_handles_files.items():
            handles_descriptions[name] = self._load_yaml(handles_file)
        return {
            'pipeline': pipeline_description,
            'handles': handles_descriptions
        }

    @property
    def jterator_project_dir(self):
        directory = os.path.join(self.directory, 'jterator')
        if not os.path.exists(directory):
            raise OSError(
                'Jterator project directory does not exist: {0}'.format(
                    directory
                )
            )
        return directory

    @property
    def _jterator_pipeline_file(self):
        filename = os.path.join(self.jterator_project_dir, 'pipeline.yaml')
        if not os.path.exists(filename):
            raise OSError(
                'Jterator pipeline description file does not exist: {0}'.format(
                    filename
                )
            )
        return filename

    @property
    def _jterator_handles_dir(self):
        directory = os.path.join(self.jterator_project_dir, 'handles')
        if not os.path.exists(directory):
            raise OSError(
                'Jterator handles directory does not exist: {0}'.format(
                    directory
                )
            )
        return directory

    @property
    def _jterator_handles_files(self):
        files = dict()
        for f in os.listdir(self._jterator_handles_dir):
            if not f.endswith('handles.yaml'):
                continue
            name = os.path.splitext(os.path.splitext(f)[0])[0]
            files[name] = os.path.join(self._jterator_handles_dir, f)
        return files

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        if isinstance(value, six.binary_type):
            value = unicode(value)
        if not isinstance(value, six.text_type):
            raise TypeError('Experiment name must be a string.')
        self._name = value

    @property
    def microscope_type(self):
        return self._microscope_type

    @microscope_type.setter
    def microscope_type(self, value):
        if isinstance(value, six.binary_type):
            value = unicode(value)
        if not isinstance(value, six.text_type):
            raise TypeError('Microscope type must be a string.')
        self._microscope_type = value

    @property
    def plate_format(self):
        return self._plate_format

    @plate_format.setter
    def plate_format(self, value):
        if not isinstance(value, int):
            raise TypeError('Plate format must be a number.')
        self._plate_format = value

    @property
    def plate_acquisition_mode(self):
        return self._plate_acquisition_mode

    @plate_acquisition_mode.setter
    def plate_acquisition_mode(self, value):
        if isinstance(value, six.binary_type):
            value = unicode(value)
        if not isinstance(value, six.text_type):
            raise TypeError('Plate acquisition mode must be a string.')
        self._plate_acquisition_mode = value

    @property
    def plates(self):
        return self._plates

    @plates.setter
    def plates(self, value):
        if not isinstance(value, list):
            raise TypeError('Plates must be a list.')
        self._plates = list()
        for v in natsorted(value):
            if not os.path.isdir(v):
                continue
            p = PlateInfo(v)
            self._plates.append(p)


class PlateInfo(object):

    def __init__(self, directory):
        self.directory = directory
        self.name = os.path.basename(self.directory)
        acquisitions_dir = os.path.join(self.directory, 'acquisitions')
        if not os.path.exists(acquisitions_dir):
            raise OSError(
                'Acquisitions directory does not exist: {0}'.format(
                    acquisitions_dir
                )
            )
        self.acquisitions = glob.glob(os.path.join(acquisitions_dir, '*'))

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        if isinstance(value, six.binary_type):
            value = unicode(value)
        if not isinstance(value, six.text_type):
            raise TypeError('Plate name must be a string.')
        self._name = value

    @property
    def acquisitions(self):
        return self._acquisitions

    @acquisitions.setter
    def acquisitions(self, value):
        if not isinstance(value, list):
            raise TypeError('Acquisitions must be a list.')
        self._acquisitions = list()
        for v in natsorted(value):
            if not os.path.isdir(v):
                continue
            a = AcquisitionInfo(v)
            self._acquisitions.append(a)


class AcquisitionInfo(object):

    def __init__(self, directory):
        self.directory = directory
        self.name = os.path.basename(self.directory)
        self.microscope_files = glob.glob(os.path.join(self.directory, '*'))

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        if isinstance(value, six.binary_type):
            value = unicode(value)
        if not isinstance(value, six.text_type):
            raise TypeError('Acquisition name must be a string.')
        self._name = value



def pytest_runtest_makereport(item, call):
    if "incremental" in item.keywords:
        if call.excinfo is not None:
            parent = item.parent
            parent._previousfailed = item


def pytest_runtest_setup(item):
    if "incremental" in item.keywords:
        previousfailed = getattr(item.parent, "_previousfailed", None)
        if previousfailed is not None:
            pytest.xfail("previous test failed (%s)" %previousfailed.name)


def _execute(command):
    subprocess.check_output(command)


def _docker_up(root_dir):
    _execute([
        'docker-compose',
        '-f', os.path.join(root_dir, 'docker-compose.yml'),
        '-f', os.path.join(root_dir, 'docker-compose.local_override.yml'),
        'up', '-d', '--force-recreate'
    ])
    _execute(['docker', 'exec', 'tissuemaps-app',
        '/home/tissuemaps/.local/bin/tm_add', 'user',
        '-n', 'devuser', '-p', '123456', '-e', 'devuser@shemail.com'
    ])


def _docker_down(root_dir):
    _execute([
        'docker-compose',
        '-f', os.path.join(root_dir, 'docker-compose.yml'),
        '-f', os.path.join(root_dir, 'docker-compose.local_override.yml'),
        'down', '-v'
    ])


@pytest.fixture(scope='session')
def experiment_info():
    directory = os.environ['TMTEST_DATA_DIR']
    return ExperimentInfo(directory)


@pytest.fixture(scope='session')
def root_dir():
    return os.path.dirname(str(pytest.config.rootdir))


@pytest.fixture(scope='session')
def client(root_dir, experiment_info):
    host = 'localhost'
    port = 8002
    username = 'devuser'
    password = '123456'

    _docker_up(root_dir)
    try:
        client = TmClient(host, port, username, password, experiment_info.name)
        yield client
    except requests.ConnectionError:
        _docker_down(root_dir)
        raise OSError(
            'Client could not connect to host "{0}" on port {1}.'.format(
                host, port
            )
        )
    _docker_down(root_dir)
