import pytest
import os.path as p
from tmaps.models import Experiment


@pytest.fixture(scope='module')
def exp(testuser):
    exp = Experiment.create(name='Some exp', description='Some desc', owner=testuser)
    return exp


def test_experiment_creation_without_specifying_location(exp, testuser):

    # Check if the properties were saved
    assert exp.name == 'Some exp'
    assert exp.description == 'Some desc'
    assert exp.owner == testuser

    assert type(exp.hash) == unicode and exp.hash != ''

    # Check if directories were created
    assert p.exists(exp.location)
    assert p.exists(p.join(exp.location, 'layers'))
    assert p.exists(p.join(exp.location, 'plates'))
    assert p.exists(p.join(exp.location, 'plate_sources'))


def test_as_dict_method(exp):
    ser = exp.as_dict()

    assert ser['id'] == exp.hash
    assert ser['name'] == exp.name
    assert ser['description'] == exp.description
    assert ser['owner'] == exp.owner.name

    assert 'layers' in ser and type(ser['layers']) == list
    assert 'plate_sources' in ser and type(ser['plate_sources']) == list
    assert 'plates' in ser and type(ser['plates']) == list


def test_lookup_by_hash(exp):
    assert Experiment.get(exp.hash) == exp
    assert Experiment.get(exp.id) == exp
