# TmDeploy - Automated deployment of TissueMAPS in the cloud.
# Copyright (C) 2016  Markus D. Herrmann, University of Zurich

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
import os
import yaml
import json
import logging

logger = logging.getLogger(__name__)


def to_json(description):
    return json.dumps(description, sort_keys=True, indent=2)


def from_json(description):
    return json.loads(description)


def to_yaml(description):
    return yaml.safe_dump(
        description, explicit_start=True, default_flow_style=False
    )


def from_yaml(description):
    return yaml.safe_load(description)


def read_json_file(filename):
    logger.debug('read JSON file: %s', filename)
    if not os.path.exists(filename):
        raise OSError('File does not exist: {0}'.format(filename))
    with open(filename) as f:
        return json.load(f)


def read_yaml_file(filename):
    logger.debug('read YAML file: %s', filename)
    if not os.path.exists(filename):
        raise OSError('File does not exist: {0}'.format(filename))
    with open(filename) as f:
        return yaml.load(f)


def write_yaml_file(filename, content):
    logger.debug('write YAML file: %s', filename)
    with open(filename, 'w') as f:
        f.write(to_yaml(content))
