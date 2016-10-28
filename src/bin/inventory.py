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


class CloudClientError(Exception):
    '''Error class for interactions with cloud clients.'''


class NoInstanceFoundError(CloudClientError):
    '''Error class for situations where no matching instance is found.'''


class MultipleInstancesFoundError(CloudClientError):
    '''Error class for situations where multiple matching instances are found.'''


def _get_host_ip_os(region, host_name, host_vars):
    import novaclient.client
    auth_url = os.getenv('OS_AUTH_URL')
    username = os.getenv('OS_USERNAME')
    password = os.getenv('OS_PASSWORD')
    project = os.getenv('OS_PROJECT_NAME')
    cloud_client = novaclient.client.Client(
        '2', username, password, project, auth_url, region_name=region
    )
    search_options = {'name': host_name}
    instances = cloud_client.servers.list(
        search_opts=search_options, detailed=True
    )
    if len(instances) > 1:
        raise MultipleInstancesFoundError(
            'More than one instance found with name "%s"' % host_name
        )
    elif len(instances) == 0:
        raise NoInstanceFoundError(
            'No instance found with name "%s"' % host_name
        )

    try:
        addresses = instances[0].addresses[host_vars['network']]
    except KeyError:
        raise CloudClientError(
            'No addresses found for network "%s"' % host_vars['network']
        )
    if len(addresses) > 1:
        raise CloudClientError(
            'More than one address found for network "%s"' % host_vars['network']
        )
    elif len(addresses) == 0:
        raise CloudClientError(
            'No address found for network "%s"' % host_vars['network']
        )
    return addresses[0]['addr']


def _get_host_ip_ec2(region, host_name, host_vars):
    import boto3
    access_id = os.getenv('AWS_ACCESS_KEY_ID')
    access_secret = os.getenv('AWS_SECRET_ACCESS_KEY')
    try:
        cloud_client = boto3.resource(
            'ec2',
            region_name=region,
            aws_access_key_id=access_id,
            aws_secret_access_key=access_secret,
        )
    except:
        raise CloudClientError(
            'Could not connect to cloud provider in region "%s".' % region
        )
    instances = cloud_client.instances.filter(
        Filters=[{'Name':'tag:Name', 'Values':[host_name]}]
    )
    addresses = list()
    for inst in instances:
        addresses.append(inst.public_ip_address)
    if len(addresses) > 1:
        raise MultipleInstancesFoundError(
            'More than one instance found with name "%s"' % host_name
        )
    elif len(addresses) == 0:
        raise NoInstanceFoundError(
            'No instance found with name "%s"' % host_name
        )
    return addresses[0]


def _get_host_ip_gce(region, host_name, host_vars):
    import googleapiclient.discovery
    from oauth2client.client import GoogleCredentials
    project = os.getenv('GCE_PROJECT')
    credentials_file = os.getenv('GCE_CREDENTIALS_FILE_PATH')
    credentials = GoogleCredentials.from_stream(credentials_file)
    cloud_client = googleapiclient.discovery.build(
        'compute', 'v1', credentials=credentials
    )
    try:
        instances = cloud_client.instances().list(
            project=project, zone=region, filter='name eq %s' % host_name
        ).execute()
    except:
        raise CloudClientError(
            'Could not connect to cloud provider for '
            'project "%s" in region "%s".' % (project, region)
        )
    instances = instances['items']
    if len(instances) > 1:
        raise MultipleInstancesFoundError(
            'More than one instance found with name "%s"' % host_name
        )
    elif len(instances) == 0:
        raise NoInstanceFoundError(
            'No instance found with name "%s"' % host_name
        )
    networks = [
        net for net in instances[0]['networkInterfaces']
        if net['name'] == host_vars['network']
    ]
    if len(networks) == 0:
        raise CloudClientError(
            'No network with name "%s".' % host_vars['network']
        )
    elif len(networks) > 1:
        raise CloudClientError(
            'More than one network with name "%s".' % host_vars['network']
        )
    addresses = [addr['natIP'] for addr in networks[0]['accessConfigs']]
    if len(addresses) > 1:
        raise CloudClientError(
            'More than one address found for network "%s"' % host_vars['network']
        )
    elif len(addresses) == 0:
        raise CloudClientError(
            'No address found for network "%s"' % host_vars['network']
        )
    return addresses[0]


def get_host_ip(provider, region, host_name, host_vars):
    if provider == 'os':
        ip = _get_host_ip_os(region, host_name, host_vars)
    elif provider == 'ec2':
        ip = _get_host_ip_ec2(region, host_name, host_vars)
    elif provider == 'gce':
        ip = _get_host_ip_gce(region, host_name, host_vars)
    else:
        raise ValueError('Provider "%s" is not supported.' % provider)
    return str(ip)


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
            host_vars = read_yaml_file(host_vars_file)
            default_host_vars = {
                'ansible_become': 'yes',
                'ansible_user': 'ubuntu',
                'ansible_ssh_private_key_file': private_key_file
            }
            host_vars.update(default_host_vars)
            if 'ansible_host' not in host_vars:
                host_vars['ansible_host'] = None
            if args.refresh:
                try:
                    host_vars['ansible_host'] = get_host_ip(
                        setup.cloud.provider, setup.cloud.region, host,
                        inventory['_meta']['hostvars'][host]
                    )
                except NoInstanceFoundError:
                    host_vars['ansible_host'] = None
                    logger.warn('no instance found for host "%s"', host_name)
            # Update inventory with host and group variables
            inventory['_meta']['hostvars'][host].update(host_vars)
            write_yaml_file(host_vars_file, host_vars)
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
