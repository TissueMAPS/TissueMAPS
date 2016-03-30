import pytest
import os.path as p

import mock

from tmaps.experiment import Experiment
from tmlib.models.plate import SUPPORTED_PLATE_FORMATS
from tmlib.models.plate import SUPPORTED_PLATE_AQUISITION_MODES
from tmlib.workflow.metaconfig import SUPPORTED_MICROSCOPE_TYPES


@pytest.fixture
def testexp(testexps):
    """Choose a single experiment for the experiment rest API unit tests."""
    return testexps['cellvoyager_384_1plate_2acquisitions_multiplexing']


def test_creation_of_experiment_object(roborobin, tmpdir):
    exp_args = {
        'root_directory': str(tmpdir),
        'name': 'Some exp',
        'description': 'Some desc',
        'user_id': roborobin.id,
        'plate_format': 96,
        'microscope_type': 'visiview',
        'plate_acquisition_mode': 'multiplexing'
    }

    def create_experiment(**kwargs):
        args = exp_args.copy()
        args.update(kwargs)
        e = Experiment(**args)
        return e


    # Only plate formats that are supported by tmlib should be accepted
    for f in SUPPORTED_PLATE_FORMATS:
        create_experiment(plate_format=f)
    with pytest.raises(ValueError) as exc:
        create_experiment(plate_format=999)

    # Description should be an optional attribute
    args = exp_args.copy()
    del args['description'] 
    e = Experiment(**args)
    assert e.description == '', \
        'Description property was not set to the empty string'

    # Only certain microscopes are supported
    for t in SUPPORTED_MICROSCOPE_TYPES:
        create_experiment(microscope_type=t)
    with pytest.raises(ValueError) as exc:
        create_experiment(microscope_type='asdf')

    for m in SUPPORTED_PLATE_AQUISITION_MODES:
        create_experiment(plate_acquisition_mode=m)
    with pytest.raises(ValueError) as exc:
        create_experiment(plate_acquisition_mode='asdf')


def test_experiment_deletion(tmpdir, roborobin, session):
    exp_args = {
        'root_directory': str(tmpdir),
        'name': 'Some exp',
        'description': 'Some desc',
        'user_id': roborobin.id,
        'plate_format': 96,
        'microscope_type': 'visiview',
        'plate_acquisition_mode': 'multiplexing'
    }

    # Don't use test experiment fixture since otherwise
    # the directory will be removed twice which will throw an exception.
    e = Experiment(**exp_args)
    session.add(e)
    session.commit()
    assert p.exists(e.location), \
        'Experiment location was not automatically created'
    session.delete(e)
    session.commit()
    assert not p.exists(e.location), \
        'Experiment location was not automatically deleted'
