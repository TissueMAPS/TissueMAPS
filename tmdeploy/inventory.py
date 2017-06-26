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
import collections
import logging
try:
    from ConfigParser import SafeConfigParser
except ImportError:
    import configparser
    SafeConfigParser = configparser.ConfigParser

from tmdeploy.utils import read_yaml_file, to_json
from tmdeploy.config import CONFIG_DIR, Setup

GROUP_VARS_DIR = os.path.join(CONFIG_DIR, 'group_vars')
HOSTS_FILE = os.path.join(CONFIG_DIR, 'hosts')

HOST_VARS_DIR = os.path.join(CONFIG_DIR, 'host_vars')

HOSTNAME_FORMAT = '{name}-{cluster}-{node_type}-{index:03d}'

logger = logging.getLogger(__name__)


def build_inventory(setup):
    '''Builds an inventory for use as part of an
    `dynamic Ansible inventory <http://docs.ansible.com/ansible/intro_dynamic_inventory.html>`_
    according to the
    `script conventions <http://docs.ansible.com/ansible/developing_inventory.html#script-conventions>`_::

        {
            "_meta" : {
                "hostvars" : {
                    "host1": {},
                    "host2": {},
                    "host3": {},
                    ...
            },
            "all": {
                "vars": {}
            },
            "group1": {
                "hosts": ["host1", "host2"],
                "vars": {}
            },
            "group2": {
                "hosts": ["host3"],
                "vars": {}
            },
            ...
        }


    Parameters
    ----------
    setup: tmdeploy.config.Setup
        setup configuration

    Returns
    -------
    dict
        mapping of groups to hosts
    '''
    inventory = dict()
    inventory['all'] = dict()
    inventory['all']['vars'] = {
        'provider': setup.cloud.provider,
        'region': setup.cloud.region,
        'key_name': setup.cloud.key_name,
        'key_file': os.path.expandvars(
            os.path.expanduser(
                setup.cloud.key_file_public
            )
        ),
        'network': setup.cloud.network,
        'subnetwork': setup.cloud.subnetwork,
        'ip_range': setup.cloud.ip_range,
    }
    inventory['_meta'] = dict()
    inventory['_meta']['hostvars'] = dict()

    if not isinstance(setup, Setup):
        raise TypeError(
            'Argument "setup" must have type {0}.'.format(
                '.'.join([Setup.__module__, Setup.__name__])
            )
        )
    for cluster in setup.architecture.clusters:
        logger.info('configure cluster "%s"', cluster.name)
        for node_type in cluster.node_types:
            logger.info('configure node type "%s"', node_type.name)
            for i in range(node_type.count):
                host_name = HOSTNAME_FORMAT.format(
                    name=setup.architecture.name, cluster=cluster.name,
                    node_type=node_type.name, index=i+1
                )
                host_vars = dict()
                for k, v in node_type.instance.to_dict().items():
                    if k == 'tags':
                        # Every server is part of the "compute-storage"
                        # security group, which is important for servers to be
                        # able to connect to each other when part of a cluster.
                        security_groups = 'compute-storage'
                        if 'web' in v:
                            host_vars['assign_public_ip'] = 'yes'
                            security_groups = ','.join([
                                security_groups, 'web'
                            ])
                        else:
                            host_vars['assign_public_ip'] = 'no'
                        host_vars['security_groups'] = security_groups
                    if isinstance(v, list):
                        v = ','.join(v)
                    host_vars[k] = v
                inventory['_meta']['hostvars'][host_name] = host_vars
                for group in node_type.groups:
                    logger.info('add group "%s"', group.name)
                    if group.name not in inventory:
                        inventory[group.name] = {'hosts': list()}
                    inventory[group.name]['hosts'].append(host_name)
                    inventory[group.name]['vars'] = dict()
                    if group.vars is not None:
                        inventory[group.name]['vars'].update(group.vars)
                    if node_type.vars is not None:
                        inventory[group.name]['vars'].update(node_type.vars)

    return inventory


def load_inventory(hosts_file=HOSTS_FILE):
    '''Loads Ansible inventory from file.

    Parameters
    ----------
    hosts_file: str, optional
        path to Ansible hosts file

    Returns
    -------
    ConfigParser.SafeConfigParser
        content of `hosts_file`
    '''
    inventory = SafeConfigParser(allow_no_value=True)
    if os.path.exists(hosts_file):
        inventory.read(hosts_file)
    else:
        logger.warn('inventory file doesn\'t exist: %s', hosts_file)
    return inventory


def save_inventory(inventory, hosts_file=HOSTS_FILE):
    '''Saves Ansible inventory to file.

    Parameters
    ----------
    inventory: ConfigParser.SafeConfigParser
        content of the `hosts_file`
    hosts_file: str, optional
        path to Ansible hosts file
    '''
    with open(hosts_file, 'w') as f:
        inventory.write(f)
