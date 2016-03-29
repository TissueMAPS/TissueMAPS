import mock
import pytest
import os.path as p
from tmaps.experiment import Experiment
import tmlib

from tmlib.models.plate import SUPPORTED_PLATE_FORMATS
from tmlib.models.plate import SUPPORTED_PLATE_AQUISITION_MODES
from tmlib.workflow.metaconfig import SUPPORTED_MICROSCOPE_TYPES


def test_creation_of_experiment_object(db, roborobin, tmpdir):

    exp_args = {
        'root_directory': tmpdir,
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
    assert e.description == ''

    # Only certain microscopes are supported
    for t in SUPPORTED_MICROSCOPE_TYPES:
        create_experiment(microscope_type=t)
    with pytest.raises(ValueError) as exc:
        create_experiment(microscope_type='asdf')

    for m in SUPPORTED_PLATE_AQUISITION_MODES:
        create_experiment(plate_acquisition_mode=m)
    with pytest.raises(ValueError) as exc:
        create_experiment(plate_acquisition_mode='asdf')


# def test_experiment_creation_without_specifying_location(exp, testuser):

#     # Check if the properties were saved
#     assert exp.name == 'Some exp'
#     assert exp.description == 'Some desc'
#     assert exp.owner == testuser

#     assert type(exp.hash) == str and exp.hash != ''

#     # Check if dir was created
#     assert p.exists(exp.location)


# def test_as_dict_method(exp):
#     ser = exp.as_dict()

#     assert ser['id'] == exp.hash
#     assert ser['name'] == exp.name
#     assert ser['description'] == exp.description
#     assert ser['owner'] == exp.owner.name

#     assert ser['plate_format'] == exp.plate_format
#     assert ser['microscope_type'] == exp.microscope_type
#     assert ser['creation_stage'] == exp.creation_stage

#     assert 'layers' in ser and type(ser['layers']) == list
#     assert 'plate_sources' in ser and type(ser['plate_sources']) == list
#     assert 'plates' in ser and type(ser['plates']) == list


# def test_lookup_by_hash(exp):
#     assert Experiment.get(exp.hash) == exp
#     assert Experiment.get(exp.id) == exp


# def test_experiment_deletion(testuser):
#     # Don't use test experiment fixture since otherwise
#     # the directory will be removed twice which will throw an exception.
#     e = Experiment.create(
#         name='Some exp', description='Some desc', owner=testuser,
#         plate_format=96, microscope_type='visiview'
#     )
#     loc = e.location
#     e.delete()
#     assert not p.exists(loc)


# def test_dataset_property(exp):
#     import h5py
#     f = h5py.File(p.join(exp.location, 'data.h5'), 'w')
#     f.create_group('/objects/cells')
#     f.create_group('/objects/nuclei')
#     f.close()

#     with exp.dataset as d:
#         assert set(d['/objects'].keys()) == {'cells', 'nuclei'}
