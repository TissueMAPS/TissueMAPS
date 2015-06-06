import re


def check_visi_config(config):
    '''
    Utility function to check whether the YAML configuration file is provided
    in the correct format.
    '''
    required_keys = [
                'FILENAME_FORMAT',
                'ACQUISITION_MODE',
                'ACQUISITION_LAYOUT'
    ]

    valid_expressions = [
                'project',
                'well',
                'site',
                'row',
                'column',
                'channel',
                'time',
                'zstack',
                'filter'
    ]

    supported_modes = [
                'ZigZagHorizontal',
                'Horizontal'
    ]

    supported_layouts = [
                'columns>rows',
                'columns<rows'
    ]

    # Ensure that YAML file specifies all required keys
    for key in required_keys:
        if key not in config.keys():
            raise Exception('YAML configuration file must specify key "%s"' %
                            key)

    # Ensure that expression in 'nomenclature_string' are also specified in
    # 'nomenclature_format'
    expressions = re.findall(r'{(\w+).*?}', config['FILENAME_FORMAT'])
    for exp in expressions:
        if exp not in valid_expressions:
            raise Exception('"{%s}" in "FILENAME_FORMAT" is not '
                            'a valid expression.' % exp)

    # Ensure that acquisition mode is supported
    if config['ACQUISITION_MODE'] not in supported_modes:
            raise Exception('Acquisition mode "%s" is not supported.'
                            'The following modes are supported:\n- %s' %
                            '\n- '.join(supported_modes))

    if config['ACQUISITION_LAYOUT'] not in supported_layouts:
            raise Exception('Acquisition layout "%s" is not supported.'
                            'The following layouts are supported:\n- %s' %
                            '\n- '.join(supported_modes))
