# TODO: create setup based on description in grid.yml file

CONFIG_DIR = os.path.expanduser('~/.tmaps/setup')


def check_setup_description(setup):
    def check_section_keys(section, required_keys, name=None, index=None, opt_keys={}):
        possible_keys = required_keys.union(opt_keys)
        if name is None:
            message = 'Setup'
            mapping = section
        else:
            if index is None:
                message = 'Section "%s" in setup' % name
                mapping = section[name]
            else:
                message = 'Item #%d of section "%s" in setup' % (index, name)
                mapping = section[name][index]
        for key in required_keys:
            if key not in mapping:
                raise KeyError(
                    'Key "%s" is missing! '
                    '%s configuration must have the following keys: "%s".' %
                    (key, message, '", "'.join(required_keys))
                )
        for key in mapping:
            if key not in possible_keys:
                raise KeyError(
                    'Key "%s" is not supported! '
                    '%s configuration can have the following keys: "%s".' %
                    (key, message, '", "'.join(possible_keys))
                )

    def check_section_type(section, required_type, name=None, index=None):
        if name is None:
            message = 'Setup'
            mapping = section
        else:
            if index is None:
                message = 'Section "%s" in setup' % name
                mapping = section[name]
            else:
                message = 'Item #%d of section "%s" in setup' % (index, name)
                mapping = section[name][index]
        type_translation = {dict: 'a mapping', list: 'an array'}
        if not isinstance(mapping, required_type):
            raise TypeError(
                '%s configuration must be %s.' %
                (message, type_translation[required_type])
            )

    def check_variable_type(variables, required_type, name):
        if required_type == str:
            required_type = basestring
        type_translation = {int: 'a number', basestring: 'a string'}
        if not isinstance(variables[name], required_type):
            raise TypeError(
                'Variable "%s" must be %s.' % (name, required_type)
            )

    check_section_type(setup, dict)
    check_section_keys(setup, {'cloud', 'grid'})
    check_section_type(setup, dict, 'cloud')
    check_section_keys(
        setup,
        {'provider', 'region', 'key_name', 'key_file'},
        'cloud'
    )
    check_section_type(setup, dict, 'grid')
    check_section_keys(setup, {'name', 'clusters'}, 'grid')
    check_section_type(setup['grid'], list, 'clusters')
    for i, cluster in enumerate(setup['grid']['clusters']):
        check_section_keys(
            setup['grid'],
            {'name', 'classes'},
            'clusters', i
        )
        check_section_type(cluster, list, 'classes')
        for j, cls in enumerate(cluster['classes']):
            check_section_keys(
                cluster,
                {'name', 'count', 'groups', 'vars'},
                'classes', j
            )
            check_section_type(cls, list, 'groups')
            check_variable_type(cls, int, 'count')
            for k in range(len(cls['groups'])):
                check_section_keys(
                    cls,
                    {'name', 'playbook'},
                    'groups', k,
                    opt_keys={'vars'}
                )
            check_section_type(cls, dict, 'vars')
            check_section_keys(
                cls,
                {'image', 'flavor', 'network', 'security_group', 'network'},
                'vars',
                opt_keys={'volume_size', 'disk_size'}
            )
            check_variable_type(cls['vars'], str, 'image')
            check_variable_type(cls['vars'], str, 'flavor')
            check_variable_type(cls['vars'], str, 'network')
            check_variable_type(cls['vars'], str, 'security_group')
            check_variable_type(cls['vars'], str, 'network')


def load_setup():
    setup_file = os.path.join(CONFIG_DIR, 'grid.yml')
    if not os.path.exists(setup_file):
        raise OSError(
            'Setup file "%s" does not exist!' % setup_file
        )
    return read_yaml_file(setup_file)

