import re


def check_visi_config(config):
    '''
    Utility function to check whether the YAML configuration file is provided
    in the correct format.
    '''
    required_keys = [
                'NOMENCLATURE_STRING',
                'NOMENCLATURE_FORMAT',
                'ACQUISITION_MODE',
                'ACQUISITION_LAYOUT'
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
    expressions = re.findall(r'{([^{}]+)}', config['NOMENCLATURE_STRING'])
    for exp in expressions:
        if exp not in config['NOMENCLATURE_FORMAT'].keys():
            raise Exception('Expression "{%s}" in "NOMENCLATURE_STRING" '
                            'needs to be specified in "NOMENCLATURE_FORMAT".' %
                            exp)

    # Ensure that number of expressions and number of tags are the same
    if len(expressions) != len(config['NOMENCLATURE_FORMAT']):
        raise Exception('Number of expressions in "NOMENCLATURE_STRING" '
                        'need to be the same as '
                        'the number of tags in "NOMENCLATURE_FORMAT".')

    # Ensure that required tags are provided in 'nomenclature_format'
    for tag in required_tags:
        if tag not in config['NOMENCLATURE_FORMAT']:
            raise Exception('"NOMENCLATURE_FORMAT" must specify key "%s"' %
                            tag)

    # Ensure that acquisition mode is supported
    if config['ACQUISITION_MODE'] not in supported_modes:
            raise Exception('Acquisition mode "%s" is not supported.'
                            'The following modes are supported:\n- %s' %
                            '\n- '.join(supported_modes))

    if config['ACQUISITION_LAYOUT'] not in supported_layouts:
            raise Exception('Acquisition layout "%s" is not supported.'
                            'The following layouts are supported:\n- %s' %
                            '\n- '.join(supported_modes))
