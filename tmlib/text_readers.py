import os
import json
import yaml
import ruamel.yaml


def load_yaml(string, use_ruamel=False):
    '''
    Convert YAML string to Python object.

    Parameters
    ----------
    string: str
        YAML string
    use_ruamel: bool, optional
        when the `ruamel.yaml` library should be used (defaults to ``False``)

    Returns
    -------
    dict or list
    '''
    if use_ruamel:
        return ruamel.yaml.load(string, ruamel.yaml.RoundTripLoader)
    else:
        return yaml.load(string)


def read_yaml(filename, use_ruamel=False):
    '''
    Read YAML file.

    Parameters
    ----------
    filename: str
        absolute path to the YAML file
    use_ruamel: bool, optional
        when the `ruamel.yaml` library should be used (defaults to ``False``)

    Returns
    -------
    dict or list
        file content

    Raises
    ------
    OSError
        when `filename` does not exist
    '''
    if not os.path.exists(filename):
        raise OSError('File does not exist: %s' % filename)
    with open(filename, 'r') as f:
        yaml_content = load_yaml(f.read(), use_ruamel)
    return yaml_content


def load_json(string):
    '''
    Convert JSON string to Python object.

    Parameters
    ----------
    string: str
        JSON string

    Returns
    -------
    dict or list
    '''
    return json.loads(string)


def read_json(filename):
    '''
    Read data from JSON file.

    Parameters
    ----------
    filename: str
        name of the JSON file

    Returns
    -------
    dict or list
        content of the JSON file

    Raises
    ------
    OSError
        when `filename` does not exist
    '''
    if not os.path.exists(filename):
        raise OSError('File does not exist: %s' % filename)
    with open(filename, 'r') as f:
        json_content = load_json(f.read())
    return json_content
