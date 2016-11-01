TmSetup - Automated setup and deployment of TissueMAPS in the cloud.
Copyright (C) 2016  Markus D. Herrmann, University of Zurich

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
import os
import collections

from tmsetup.utils import read_yaml_file, to_json
from tmsetup.config import CONFIG_DIR, Setup


GROUP_VARS_DIR = os.path.join(CONFIG_DIR, 'group_vars')
HOST_VARS_DIR = os.path.join(CONFIG_DIR, 'host_vars')
HOSTS_FILE = os.path.join(CONFIG_DIR, 'hosts')

HOSTNAME_FORMAT = '{grid}-{cluster}-{node_type}-{index:03X}'


def build_inventory_information(setup):
    '''Builds inventory information for use as part of an
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
    setup: tmsetup.config.Setup
        setup configuration

    Returns
    -------
    dict
        mapping of groups to hosts
    '''
    inventory = dict()
    inventory['all'] = dict()
    inventory['_meta'] = dict()
    inventory['_meta']['hostvars'] = dict()

    if not isinstance(setup, Setup):
        raise TypeError(
            'Argument "setup" must have type tmsetup.config.Setup.'
        )
    for cluster in setup.grid.clusters:
        for node_type in cluster.node_types:
            for i in range(node_type.count):
                host_name = HOSTNAME_FORMAT.format(
                    grid=setup.grid.name, cluster=cluster.name,
                    node_type=node_type.name, index=i+1
                )
                inventory['_meta']['hostvars'][host_name] = \
                    node_type.instance.to_dict()
                for group in node_type.groups:
                    if group.name not in inventory:
                        inventory[group.name] = {'hosts': list()}
                    inventory[group.name]['hosts'].append(host_name)
                    if group.vars is not None:
                        inventory[group.name]['vars'] = group.vars
                    inventory['all']['vars'] = {
                        'provider': setup.cloud.provider,
                        'region': setup.cloud.region,
                        'key_name': setup.cloud.key_name,
                        'key_file': os.path.expandvars(
                            os.path.expanduser(
                                setup.cloud.key_file_public
                            )
                        ),
                    }

    return inventory


def load_inventory():
    '''Loads Ansible inventory from file.

    Returns
    -------
    ConfigParser.SafeConfigParser
    '''
    if not os.path.exists(HOSTS_FILE):
        raise OSError(
            'Setup file "%s" does not exist!' % HOSTS_FILE
        )
    inventory = SafeConfigParser(allow_no_value=True)
    inventory.read(HOSTS_FILE)
    return inventory


def save_inventory(inventory):
    '''Saves Ansible inventory to file.

    Parameters
    ----------
    inventory: ConfigParser.SafeConfigParser
    '''
    with open(HOSTS_FILE, 'w') as f:
        inventory.write(f)
