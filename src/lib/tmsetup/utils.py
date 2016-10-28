import os
import yaml
import json


def to_json(description):
    return json.dumps(description, sort_keys=True, indent=2)


def from_json(description):
    return json.loads(description)


def to_yaml(description):
    return yaml.dump(description, explicit_start=True, default_flow_style=False)


def from_yaml(description):
    return yaml.load(description)


def read_json_file(filename):
    if not os.path.exists(filename):
        raise OSError('File does not exist: %s', filename)
    with open(filename) as f:
        return json.load(f)

def read_yaml_file(filename):
    if not os.path.exists(filename):
        raise OSError('File does not exist: %s', filename)
    with open(filename) as f:
        return yaml.load(f)


def write_yaml_file(filename, content):
    with open(filename, 'w') as f:
        f.write(to_yaml(content))
