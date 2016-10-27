#!/usr/bin/env python

import os
import collections
import argparse
import sys
import logging
from ConfigParser import SafeConfigParser

from tmsetup.utils import write_yaml_file, read_yaml_file, to_json
from tmsetup.config import Setup, load_inventory, save_inventory
from tmsetup.config import CONFIG_DIR, GROUP_VARS_DIR, HOST_VARS_DIR
from tmsetup.config import HOSTNAME_FORMAT


def build_inventory(setup):
    inventory = dict()
    inventory['all'] = dict()
    inventory['_meta'] = dict()
    inventory['_meta']['hostvars'] = collections.defaultdict(dict)

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
                        'key_name': setup.cloud.key_name,
                        'key_file': os.path.expandvars(
                            os.path.expanduser(
                                setup.cloud.key_file_public
                            )
                        ),
                        'region': setup.cloud.region,
                    }

    return inventory


def main(args):

    if not os.path.exists(CONFIG_DIR):
        raise OSError(
            'Configuration directory "%s" does not exist!' % CONFIG_DIR
        )

    setup = Setup()

    if not os.path.exists(GROUP_VARS_DIR):
        os.mkdir(GROUP_VARS_DIR)
    if not os.path.exists(HOST_VARS_DIR):
        os.mkdir(HOST_VARS_DIR)

    inventory = build_inventory(setup)
    inventory['all']['vars']['host_vars_dir'] = HOST_VARS_DIR

    # Create the main ansible inventory file
    persistent_inventory = load_inventory()
    for group, group_content in inventory.iteritems():
        if group == '_meta':
            continue

        # Create a separate variable file in YAML format for each group
        group_vars_file = os.path.join(GROUP_VARS_DIR, group)
        if group_content.get('vars', None) is not None:
            write_yaml_file(group_vars_file, group_content['vars'])

        if group == 'all':
            continue

        if not persistent_inventory.has_section(group):
            persistent_inventory.add_section(group)
        for host in inventory[group]['hosts']:
            persistent_inventory.set(group, host)
            # Create a separte variable file in YAML format for each host
            host_vars_file = os.path.join(HOST_VARS_DIR, host)
            private_key_file = os.path.expandvars(
                os.path.expanduser(setup.cloud.key_file_private)
            )
            if not os.path.exists(host_vars_file):
                host_vars = {
                    'ansible_host': '',
                    'ansible_user': 'ubuntu',
                    'ansible_ssh_private_key_file': private_key_file
                }
                write_yaml_file(host_vars_file, host_vars)
            # Update inventory with host and group variables
            host_vars = read_yaml_file(host_vars_file)
            host_vars['ansible_ssh_private_key_file'] = private_key_file
            inventory['_meta']['hostvars'][host].update(host_vars)
            # TODO: check whether this host actually exists in the cloud
            # args.refresh

        # Remove group_vars and host_vars files when the respective group or
        # host is no longer part of the inventory.
        for group in os.listdir(GROUP_VARS_DIR):
            if group == 'all':
                continue
            if group not in inventory:
                group_vars_file = os.path.join(GROUP_VARS_DIR, group)
                os.remove(group_vars_file)
        for host in os.listdir(HOST_VARS_DIR):
            if host not in inventory['_meta']['hostvars']:
                host_vars_file = os.path.join(HOST_VARS_DIR, host)
                os.remove(host_vars_file)

    # Create (or update) the main ansible inventory file in INI format
    save_inventory(persistent_inventory)

    # Prin the inventory to standard output as required for a dynamic
    # ansible inventory:
    # (http://docs.ansible.com/ansible/developing_inventory.html)
    if args.list:
        print to_json(inventory)
    elif args.host:
        print to_json(inventory['_meta']['hostvars'][args.host])

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Dynamic Ansible inventory')
    parser.add_argument(
        '--private', action='store_true',
        help='Use private address for ansible host'
    )
    parser.add_argument(
        '--refresh', action='store_true',
        help='Refresh cached information'
    )
    parser.add_argument(
        '--debug', action='store_true',
        help='Enable debug output'
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        '--list', action='store_true',
        help='List active servers'
    )
    group.add_argument(
        '--host',
        help='List details about the specific host'
    )
    args = parser.parse_args()
    main(args)
