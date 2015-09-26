import json
import yaml
import ruamel.yaml


def write_yaml(filename, data, use_ruamel=False):
    '''
    Write data to YAML file.

    Parameters
    ----------
    filename: str
        name of the YAML file
    data: list or dict
        description that should be written to file
    use_ruamel: bool, optional
        when the `ruamel.yaml` library should be used (defaults to ``False``)

    Note
    ----
    `filename` will be overwritten in case it already exists.
    '''
    with open(filename, 'w') as f:
        if use_ruamel:
            f.write(ruamel.yaml.dump(data,
                    Dumper=ruamel.yaml.RoundTripDumper, explicit_start=True))
        else:
            f.write(yaml.dump(data,
                    default_flow_style=False, explicit_start=True))


def write_json(filename, data, naicify=False):
    '''
    Write data to JSON file.

    Parameters
    ----------
    filename: str
        name of the JSON file
    data: list or dict
        description that should be written to file
    naicify: bool, optional
        whether `data` should be naicely formatted (default: ``False``);
        note that this will increase the size of the output file significantly

    Note
    ----
    `filename` will be overwritten in case it already exists.
    '''
    with open(filename, 'w') as f:
        if naicify:
            json.dump(data, f, sort_keys=True,
                      indent=4, separators=(',', ': '))
        else:
            json.dump(data, f, sort_keys=True)
