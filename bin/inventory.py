#!/usr/bin/env python

import os
import collections
import argparse
import sys
import logging
from ConfigParser import SafeConfigParser

from tmsetup.utils import write_yaml_file, read_yaml_file
from tmsetup.description import load_setup
from tmsetup.description import CONFIG_DIR


def build_inventory(setup):
    inventory = dict()
    inventory['all'] = dict()
    inventory['_meta'] = dict()
    inventory['_meta']['hostvars'] = collections.defaultdict(dict)

    for cluster in setup['grid']['clusters']:
        for cls in cluster['classes']:
            class_name = '%s-%s-%s' % (
                setup['grid']['name'], cluster['name'], cls['name']
            )
            for i in range(cls['count']):
                host_name = '%s-%.3d' % (class_name, i+1)
                inventory['_meta']['hostvars'][host_name] = cls['vars']
                for group in cls['groups']:
                    if group['name'] not in inventory:
                        inventory[group['name']] = {'hosts': list()}
                    inventory[group['name']]['hosts'].append(host_name)
                    if group.get('vars', None) is not None:
                        inventory[group['name']]['vars'] = group['vars']
                    inventory['all']['vars'] = {
                        'provider': setup['cloud']['provider'],
                        'key_name': setup['cloud']['key_name'],
                        'key_file': os.path.expanduser(setup['cloud']['key_file']),
                        'region': setup['cloud']['region'],
                    }

    return inventory


def main(args):

    if not os.path.exists(CONFIG_DIR):
        raise OSError(
            'Configuration directory "%s" does not exist!' % CONFIG_DIR
        )

    setup = load_setup()

    group_vars_dir = os.path.join(CONFIG_DIR, 'group_vars')
    if not os.path.exists(group_vars_dir):
        os.mkdir(group_vars_dir)
    host_vars_dir = os.path.join(CONFIG_DIR, 'host_vars')
    if not os.path.exists(host_vars_dir):
        os.mkdir(host_vars_dir)

    inventory = build_inventory(setup)
    inventory['all']['vars']['host_vars_dir'] = host_vars_dir

    # Create the main ansible inventory file
    inventory_file = os.path.join(CONFIG_DIR, 'hosts')
    inventory_file_content = SafeConfigParser(allow_no_value=True)
    for group, group_content in inventory.iteritems():
        if group == '_meta':
            continue

        # Create a separate variable file in YAML format for each group
        group_vars_file = os.path.join(group_vars_dir, group)
        if group_content.get('vars', None) is not None:
            write_yaml_file(group_vars_file, group_content['vars'])

        if group == 'all':
            continue

        inventory_file_content.add_section(group)
        for host in inventory[group]['hosts']:
            inventory_file_content.set(group, host)
            # Create a separte variable file in YAML format for each host
            host_vars_file = os.path.join(host_vars_dir, host)
            key_file = os.path.expanduser(setup['cloud']['key_file'])
            if not os.path.exists(host_vars_file):
                host_vars = {
                    'ansible_ssh_host': '',
                    'ansible_ssh_user': 'ubuntu',
                    'ansible_ssh_private_key_file': key_file
                }
                write_yaml_file(host_vars_file, host_vars)
            # Update inventory with host and group variables
            host_vars = read_yaml_file(host_vars_file)
            host_vars['ansible_ssh_private_key_file'] = key_file
            inventory['_meta']['hostvars'][host].update(host_vars)
            # TODO: check whether this host actually exists in the cloud
            # args.refresh

        # Remove group_vars and host_vars files when the respective group or
        # host is no longer part of the inventory.
        for group in os.listdir(group_vars_dir):
            if group == 'all':
                continue
            if group not in inventory:
                group_vars_file = os.path.join(group_vars_dir, group)
                os.remove(group_vars_file)
        for host in os.listdir(host_vars_dir):
            if host not in inventory['_meta']['hostvars']:
                host_vars_file = os.path.join(host_vars_dir, host)
                os.remove(host_vars_file)

    # Create (or update) the main ansible inventory file in INI format
    inventory_file_content.read(inventory_file)
    with open(inventory_file, 'w') as f:
        inventory_file_content.write(f)

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
