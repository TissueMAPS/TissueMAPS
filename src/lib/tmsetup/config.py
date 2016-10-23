import os
from abc import ABCMeta
from abc import abstractproperty
from ConfigParser import SafeConfigParser

from tmsetup.utils import read_yaml_file
from tmsetup.errors import SetupDescriptionError, SetupEnvironmentError


CONFIG_DIR = os.path.expanduser('~/.tmaps/setup')
GROUP_VARS_DIR = os.path.join(CONFIG_DIR, 'group_vars')
HOST_VARS_DIR = os.path.join(CONFIG_DIR, 'host_vars')
HOSTS_FILE = os.path.join(CONFIG_DIR, 'hosts')
SETUP_FILE = os.path.join(CONFIG_DIR, 'grid.yml')


class SetupSection(object):

    __meta__ = ABCMeta

    def __init__(self, description):
        if not isinstance(description, dict):
            raise SetupDescriptionError(
                'Section "%s" of setup description must be a mapping.' %
                self._section_name
            )
        possible_attrs = set([
            attr for attr in dir(self) if not attr.startswith('_')
        ])
        if hasattr(self.__class__, '_OPTIONAL_ATTRS'):
            required_attrs = possible_attrs - self.__class__._OPTIONAL_ATTRS
        else:
            required_attrs = possible_attrs
        for k, v in description.iteritems():
            if k not in possible_attrs:
                raise SetupDescriptionError(
                    'Key "%s" is not supported for section "%s".' % (
                        k, self._section_name
                    )
                )
            setattr(self, k, v)
        for k in required_attrs:
            if k not in description:
                raise SetupDescriptionError(
                    'Key "%s" is required for section "%s".' % (
                        k, self._section_name
                    )
                )

    @abstractproperty
    def _section_name(self):
        pass

    def _check_value_type(self, value, name, required_type):
        if required_type == str:
            required_type = basestring
        type_translation = {
            int: 'a number', basestring: 'a string',
            dict: 'a mapping', list: 'an array'
        }
        if not isinstance(value, required_type):
            raise SetupDescriptionError(
                'Value of "%s" in section "%s" must be %s.' % (
                    name, self._section_name, type_translation[required_type]
                )
            )

    def _check_subsection_type(self, value, name, required_type, index=None):
        if index is None:
            message = 'Subsection "%s" in setup' % name
            mapping = value
        else:
            message = 'Item #%d of subsection "%s" in setup' % (index, name)
            mapping = value[index]
        type_translation = {dict: 'a mapping', list: 'an array'}
        if not isinstance(mapping, required_type):
            raise SetupDescriptionError(
                '%s configuration must be %s.' % (
                    message, type_translation[required_type]
                )
            )

class CloudSection(SetupSection):

    def __init__(description):
        super(_CloudSection).__init__(self, description)

    @property
    def _section_name(self):
        return 'cloud'

    @property
    def provider(self):
        '''str: name of the cloud provider (options: ``{"os", "ec2", "gce"}``)
        '''
        return self._provider

    @provider.setter
    def provider(self, value):
        self._check_value_type(value, 'provider', str)
        options = {'os', 'gce', 'ec2'}
        if value not in options:
            raise SetupDescriptionError(
                'Cloud provider must be one of the following: "%s"' %
                '", "'.join(options)
            )
        if value == 'os':
            required_env_vars = {
                'OS_AUTH_URL',
                'OS_USERNAME',
                'OS_PASSWORD',
                'OS_PROJECT_NAME'
            }
        elif value == 'gce':
            required_env_vars = {
                'GCE_EMAIL',
                'GCE_PROJECT',
                'GCE_CREDENTIALS_FILE_PATH'
            }
        elif value == 'ec2':
            required_env_vars = {
                'AWS_ACCESS_KEY_ID',
                'AWS_SECRET_ACCESS_KEY'
            }
        for var in required_env_vars:
            if var not in os.environ:
                raise SetupEnvironmentError(
                    'Environment variable "%s" must be set for "%s" provider.'
                    % (var, value)
                )
        self._provider = value

    @property
    def key_name(self):
        '''str: name of the key-pair used to connect to virtual machines'''
        return self._key_name

    @key_name.setter
    def key_name(self, value):
        self._check_value_type(value, 'key_name', str)
        self._key_name = value

    @property
    def key_file(self):
        '''str: name of the key-pair used to connect to virtual machines'''
        return self._key_name

    @key_file.setter
    def key_file(self, value):
        self._check_value_type(value, 'key_file', str)
        if value.endswith('.pem'):
            raise SetupDescriptionError(
                'Value of "key_file" must point to a public key file.' % value
            )
        if not os.path.exists(value):
            raise SetupDescriptionError(
                'Public key file "%s" does not exist.' % value
            )
        self._key_name = value

    @property
    def region(self):
        '''str: cloud region (zone)'''
        return self._region

    @region.setter
    def region(self, value):
        self._check_value_type(value, 'region', str)
        self._region = value


class GridSection(SetupSection):

    def __init__(self, description):
        super(GridSection, self).__init__(description)

    @property
    def _section_name(self):
        return 'grid'

    @property
    def name(self):
        '''str: name of the grid'''
        return self._name

    @name.setter
    def name(self, value):
        self._check_value_type(value, 'name', str)

    @property
    def clusters(self):
        '''List[tmsetup.config.ClusterSection]: clusters that should be set up
        '''
        return self._clusters

    @clusters.setter
    def clusters(self, value):
        self._clusters = list()
        self._check_subsection_type(value, 'clusters', list)
        for i, item in enumerate(value):
            self._check_subsection_type(value, 'clusters', dict, index=i)
            self._clusters.append(ClusterSection(item))
        return self._clusters


class ClusterSection(SetupSection):

    def __init__(self, description):
        super(ClusterSection, self).__init__(description)

    @property
    def _section_name(self):
        return 'cluster'

    @property
    def name(self):
        '''str: name of the cluster'''
        return self._name

    @name.setter
    def name(self, value):
        self._check_value_type(value, 'name', str)

    @property
    def categories(self):
        '''List[tmsetup.config.ClusterCategorySection]: category of virtual
        machines the cluster is comprised of
        '''
        return self._categories

    @categories.setter
    def categories(self, value):
        self._categories = list()
        self._check_subsection_type(value, 'categories', list)
        for i, item in enumerate(value):
            self._check_subsection_type(value, 'categories', dict, index=i)
            self._categories.append(ClusterCategorySection(item))
        return self._categories


class ClusterCategorySection(SetupSection):

    _OPTIONAL_ATTRS = {'vars'}

    def __init__(self, description):
        super(ClusterCategorySection, self).__init__(description)

    @property
    def _section_name(self):
        return 'categories'

    @property
    def name(self):
        '''str: name of the cluster category'''
        return self._name

    @name.setter
    def name(self, value):
        self._check_value_type(value, 'name', str)

    @property
    def count(self):
        '''int: number of virtual machines'''
        return self._name

    @count.setter
    def count(self, value):
        self._check_value_type(value, 'count', int)

    @property
    def vars(self):
        '''AnsibleHostVariableSection: variables required for managing the
        virtual machine instances via Ansible (optional)
        '''
        return self._name

    @vars.setter
    def vars(self, value):
        self._check_value_type(value, 'vars', dict)
        self._vars = AnsibleHostVariableSection(value)

    @property
    def groups(self):
        '''List[tmsetup.config.AnsibleGroupSection]: Ansible host groups
        that should be used for deployment of virtual machines beloning
        to the cluster category
        '''
        return self._groups

    @groups.setter
    def groups(self, value):
        self._groups = list()
        self._check_subsection_type(value, 'groups', list)
        for i, item in enumerate(value):
            self._check_subsection_type(value, 'groups', dict, index=i)
            self._groups.append(AnsibleGroupSection(item))
        return self._groups


class AnsibleGroupSection(SetupSection):

    def __init__(self, description):
        super(AnsibleGroupSection, self).__init__(description)

    @property
    def _section_name(self):
        return 'groups'

    @property
    def name(self):
        '''str: name of the Ansible group'''
        return self._name

    @name.setter
    def name(self, value):
        self._check_value_type(value, 'name', str)

    @property
    def playbook(self):
        return self._playbook

    @playbook.setter
    def playbook(self, value):
        self._check_value_type(value, 'playbook', str)
        self._playbook = os.path.expanduser(value)
        if not os.path.isabs(self._playbook):
            self._playbook = os.path.abspath(
                os.path.join(__file__, '..', '..', '..', 'playbooks', value)
            )
        if not os.path.exists(value):
            raise SetupDescriptionError(
                'Playbook "%s" does not exist.' % value
            )

    @property
    def vars(self):
        '''dict: mapping of Ansible variable key-value pairs'''
        return self._vars

    @vars.setter
    def vars(self, value):
        if value is None:
            self._vars = value
        else:
            self._check_value_type(value, 'vars', dict)
            self._vars = value


class AnsibleHostVariableSection(SetupSection):

    _OPTIONAL_ATTRS = {'disk_size', 'volume_size'}

    def __init__(self, description):
        super(AnsibleHostVariableSection, self).__init__(description)

    @property
    def _section_name(self):
        return 'vars'

    @property
    def disk_size(self):
        '''int: size of the boot disk of the virtual machine in GB (optional)
        '''
        return self._disk_size

    @disk_size.setter
    def disk_size(self, value):
        self._check_value_type(value, 'disk_size', int)
        self._disk_size = value

    @property
    def volume_size(self):
        '''int: size of an additional storage volume in GB (optional)'''
        return self._volume_size

    @volume_size.setter
    def volume_size(self, value):
        self._check_value_type(value, 'volume_size', int)
        self._volume_size = value

    @property
    def image(self):
        '''str: name or ID of the image from which the virtual machine should
        be booted
        '''
        return self._image

    @image.setter
    def image(self, value):
        self._check_value_type(value, 'image', str)
        self._image = value

    @property
    def flavor(self):
        '''str: name or ID of the flavor (machine type) which the virtual
        machine should have
        '''
        return self._flavor

    @flavor.setter
    def flavor(self, value):
        self._check_value_type(value, 'flavor', str)
        self._flavor = value

    @property
    def security_group(self):
        '''str: name or ID of the security_group (firewall) that should be
        assigned to the virtual machine
        '''
        return self._security_group

    @security_group.setter
    def security_group(self, value):
        self._check_value_type(value, 'security_group', str)
        self._security_group = value

    @property
    def network(self):
        '''str: name or ID of the network that should be used for the virtual
        machine
        '''
        return self._network

    @network.setter
    def network(self, value):
        self._check_value_type(value, 'network', str)
        self._network = value


class Setup(object):

    def __init__(self, description_file=SETUP_FILE):
        if not os.path.exists(description_file):
            raise OSError(
                'Setup description file "%s" does not exist!' % description_file
            )
        self.description_file = description_file
        description = self._load_description()
        for k, v in description.iteritems():
            if k not in dir(self):
                raise SetupDescriptionError(
                    'Setup description requires key "%s".' % k
                )
            setattr(self, k, v)

    def _load_description(self):
        description = read_yaml_file(SETUP_FILE)
        if not isinstance(description, dict):
            raise SetupDescriptionError(
                'Setup description must be a mapping.'
            )
        return description

    @property
    def cloud(self):
        '''tmsetup.config.CloudSection: cloud configuration'''
        return self._cloud

    @cloud.setter
    def cloud(self, value):
        self._cloud = CloudSection(value)

    @property
    def grid(self):
        '''tmsetup.config.GridSection: TissueMAPS grid setup'''
        return self._grid

    @grid.setter
    def grid(self, value):
        self._grid = GridSection(value)


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
