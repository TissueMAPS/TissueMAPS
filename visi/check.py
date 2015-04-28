import re


def check_yaml_configuration(config):
    '''
    Utility function to check whether the YAML configuration file is provided
    in the correct format.
    '''
    required_keys = [
                'nomenclature_string',
                'nomenclature_format',
                'acquisition_mode',
                'acquisition_layout'
    ]

    supported_modes = [
                'ZigZagHorizontal',
                'Horizontal'
    ]

    supported_layouts = [
                'columns>rows',
                'columns<rows'
    ]

    required_tags = [
                'project',
                'site'
    ]

    # Ensure that YAML file specifies all required keys
    for key in required_keys:
        if key not in config.keys():
            raise Exception('YAML configuration file must specify key "%s"' %
                            key)

    # Ensure that expression in 'nomenclature_string' are also specified in
    # 'nomenclature_format'
    expressions = re.findall(r'{([^{}]+)}', config['nomenclature_string'])
    for exp in expressions:
        if exp not in config['nomenclature_format'].keys():
            raise Exception('Expression "{%s}" in "nomenclature_string" '
                            'needs to be specified in "nomenclature_format".' %
                            exp)

    # Ensure that required tags are provided in 'nomenclature_format'
    for tag in required_tags:
        if tag not in config['nomenclature_format']:
            raise Exception('"nomenclature_format" must specify key "%s"' %
                            tag)

    # Ensure that acquisition mode is supported
    if config['acquisition_mode'] not in supported_modes:
            raise Exception('Acquisition mode "%s" is not supported.'
                            'The following modes are supported:\n- %s' %
                            '\n- '.join(supported_modes))

    if config['acquisition_layout'] not in supported_layouts:
            raise Exception('Acquisition layout "%s" is not supported.'
                            'The following layouts are supported:\n- %s' %
                            '\n- '.join(supported_modes))
