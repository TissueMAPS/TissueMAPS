import mock
import pytest
import os.path as p
from tmaps.models import Experiment, SUPPORTED_MICROSCOPE_TYPES


@pytest.fixture()
def exp(testuser, request):
    exp = Experiment.create(
        name='Some exp', description='Some desc', owner=testuser,
        plate_format=96, microscope_type='visiview'
    )
    request.addfinalizer(lambda: exp.delete())

    return exp


def test_creation_of_experiment_object(testuser):

    # Only plate formats that are supported by tmlib should be accepted
    from tmlib import plate as tmlib_plate
    for plate_format in tmlib_plate.Plate.SUPPORTED_PLATE_FORMATS:
        e = Experiment(
            name='Some exp', description='Some desc', owner=testuser,
            plate_format=plate_format, microscope_type='visiview'
        )
    with pytest.raises(ValueError) as exc:
        e = Experiment(
            name='Some exp', description='Some desc', owner=testuser,
            plate_format=999, microscope_type='visiview'
        )

    # Description should be an optional attribute
    e = Experiment(
        name='Some exp', owner=testuser,
        plate_format=96, microscope_type='visiview'
    )
    assert e.description == ''

    # Initial stage should be 'waiting_for_upload'
    assert e.creation_stage == 'WAITING_FOR_UPLOAD'

    # Only certain microscopes are supported
    for t in SUPPORTED_MICROSCOPE_TYPES:
        e = Experiment(
            name='Some exp', description='Some desc', owner=testuser,
            plate_format=plate_format, microscope_type=t
        )
    with pytest.raises(ValueError) as exc:
        e = Experiment(
            name='Some exp', description='Some desc', owner=testuser,
            plate_format=plate_format, microscope_type='asdf'
        )


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

    assert ser['plate_format'] == exp.plate_format
    assert ser['microscope_type'] == exp.microscope_type
    assert ser['creation_stage'] == exp.creation_stage

    assert 'layers' in ser and type(ser['layers']) == list
    assert 'plate_sources' in ser and type(ser['plate_sources']) == list
    assert 'plates' in ser and type(ser['plates']) == list


def test_lookup_by_hash(exp):
    assert Experiment.get(exp.hash) == exp
    assert Experiment.get(exp.id) == exp


def test_experiment_deletion(testuser):
    # Don't use test experiment fixture since otherwise
    # the directory will be removed twice which will throw an exception.
    e = Experiment.create(
        name='Some exp', description='Some desc', owner=testuser,
        plate_format=96, microscope_type='visiview'
    )
    loc = e.location
    e.delete()
    assert not p.exists(loc)
