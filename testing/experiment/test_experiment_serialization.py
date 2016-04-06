import json

import flask


def test_serialize_experiment(app, testexp):
    serexp = json.loads(flask.json.dumps(testexp))

    assert serexp['id'] == testexp.hash
    assert serexp['name'] == testexp.name
    assert serexp['description'] == testexp.description
    assert serexp['plate_format'] == testexp.plate_format
    assert serexp['microscope_type'] == testexp.microscope_type
    assert serexp['plate_acquisition_mode'] == testexp.plate_acquisition_mode
    assert serexp['status'] == testexp.status
    assert len(serexp['channels']) == 1
    assert type(serexp['channels'][0]) is dict
    assert len(serexp['mapobject_info']) == 0
    assert len(serexp['plates']) == 0
