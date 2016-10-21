#!/usr/bin/python

import collections
import argparse
import sys
import yaml
import json


def parse_args():
    parser = argparse.ArgumentParser(description='OpenStack Inventory Module')
    parser.add_argument('--private',
                        action='store_true',
                        help='Use private address for ansible host')
    parser.add_argument('--refresh', action='store_true',
                        help='Refresh cached information')
    parser.add_argument('--debug', action='store_true', default=False,
                        help='Enable debug output')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--list', action='store_true',
                       help='List active servers')
    group.add_argument('--host', help='List details about the specific host')

    return parser.parse_args()


def to_json(in_dict):
    return json.dumps(in_dict, sort_keys=True, indent=2)


def main():
    args = parse_args()

    config_file = '/home/ubuntu/instances.yml'
    with open(config_file) as f:
        description = yaml.load(f)

    inventory = dict()
    inventory['_meta'] = dict()
    inventory['_meta']['hostvars'] = collections.defaultdict(dict)
    inventory['vm_instances'] = dict()
    inventory['vm_instances']['hosts'] = list()

    for cluster in description['clusters']:
        for cls in cluster['classes']:
            class_name = '%s-%s-%s' % (
                description['grid'], cluster['name'], cls['name']
            )
            for i in range(cls['count']):
                host_name = '%s-%.3d' % (class_name, i+1)
                for grp in cls['groups']:
                    if grp not in inventory:
                        inventory[grp] = {'hosts': list()}
                    inventory[grp]['hosts'].append(host_name)
                    inventory['vm_instances']['hosts'].append(host_name)
                    inventory['vm_instances']['vars'] = {
                        'cloud_provider': description['cloud_provider'],
                        'cloud_key_name': description['key_name'],
                        'cloud_region': description['cloud_region']
                    }
                inventory['_meta']['hostvars'][host_name] = cls['vars']

    if args.list:
        print to_json(inventory)
    elif args.host:
        print to_json(inventory['_meta'][args.host])

if __name__ == "__main__":
    main()
