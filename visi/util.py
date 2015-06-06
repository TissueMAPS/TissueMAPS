import re


def check_visi_config(config):
    '''
    Utility function to check whether the YAML configuration file is provided
    in the correct format.
    '''
    required_keys = [
                'NOMENCLATURE_STRING',
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

    # Ensure that YAML file specifies all required keys
    for key in required_keys:
        if key not in config.keys():
            raise Exception('YAML configuration file must specify key "%s"' %
                            key)

    # Ensure that acquisition mode is supported
    if config['ACQUISITION_MODE'] not in supported_modes:
            raise Exception('Acquisition mode "%s" is not supported.'
                            'The following modes are supported:\n- %s' %
                            '\n- '.join(supported_modes))

    if config['ACQUISITION_LAYOUT'] not in supported_layouts:
            raise Exception('Acquisition layout "%s" is not supported.'
                            'The following layouts are supported:\n- %s' %
                            '\n- '.join(supported_modes))
