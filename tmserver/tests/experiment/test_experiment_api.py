import uuid
import os.path as p
import os
import pytest
import numpy as np
import mock
import json
import tmserver
from tmlib.models import Experiment, Feature, MapobjectType

#
# GET EXPERIMENTS
#
def test_get_experiments_without_login(anybody):
    resp = anybody.get('/api/experiments')
    assert resp.status_code == 401


def test_get_experiments_with_login(rr):
    resp = rr.browser.get('/api/experiments')
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert 'experiments' in data

#
# GET EXPERIMENT
#
def test_get_single_experiment_without_login(anybody, testexp):

    resp = anybody.get('/api/experiments/' + testexp.hash)
    assert resp.status_code == 401, \
        'An experiment should only be requestable by logged in users'


def test_get_single_experiment_with_login(rr, rm, testexp):
    # Test the case where the user has access to the experiment
    resp = rr.browser.get('/api/experiments/' + testexp.hash)
    assert resp.status_code == 200, \
        'A user should be able to GET his own experiments.'

    resp = rr.browser.get('/api/experiments/' + 'bogus_hash')
    assert resp.status_code == 404, \
        'If no experiment can be found, a 404 response should be sent'

    resp = rm.browser.get('/api/experiments/' + testexp.hash)
    assert resp.status_code == 401, \
        'An experiment should only be accessable its owner'

#
# CREATE EXPERIMENT
#
def create_experiment_request(): 
    """Helper function to create request payloads for testing
    the API functions to create experiments.
    The name is a UUID since there is a constraint that each user has to have
    unique experiment names.

    """
    experiment_request = {
        'name': str(uuid.uuid4()),
        'description': 'Some desc',
        'microscope_type': 'visiview',
        'plate_acquisition_mode': 'multiplexing',
        'plate_format': 96
    }
    return experiment_request


def test_create_experiment_without_login(anybody, session):
    req = create_experiment_request()
    resp = anybody.post(
        '/api/experiments',
        data=json.dumps(req)
    )
    assert resp.status_code == 401, \
        'Server did not respond with status code 401'
    assert session.query(Experiment).filter_by(name=req['name']).first() is None, \
        'Experiment was added despite insufficient credentials'


def test_create_experiment_with_login(rr, db, monkeypatch):
    req = create_experiment_request()
    resp = rr.browser.post(
        '/api/experiments',
        data=json.dumps(req)
    )
    assert resp.status_code == 200

    # Check return value
    resp = json.loads(resp.data)
    assert 'experiment' in resp
    serialized_exp = resp['experiment']

    # Check if the experiment was added to the db correctly
    assert db.session.query(Experiment).filter_by(name=req['name']).first() is not None

    # Check if the returned experiment is the same as the added one
    e = db.session.query(Experiment).get_with_hash(serialized_exp['id'])
    assert e.hash == serialized_exp['id']

    # Delete the exp again
    db.session.delete(e)
    db.session.commit()

#
# DELETE EXPERIMENT
#
def test_delete_experiment(rr, testexp, session):
    # monkeypatch.setattr(db.session, 'delete', fake_delete)
    assert session.query(Experiment).get(testexp.id) is not None, \
        'Test experiment of fixture not present in database'
    response = rr.browser.delete('/api/experiments/%s' % testexp.hash)
    assert response.status_code == 200
    assert session.query(Experiment).get(testexp.id) is None, \
        'Experiment was not successfully deleted after DELETE request'

#
# GET IMAGE TILE
#
def test_get_image_tile(rr, testexp, monkeypatch, session):
    fake_method = mock.Mock(return_value=('ok', 200))
    layer = testexp.channels[0].layers[0]
    filename = 'some/path/to/a/file/tile.jpg'
    monkeypatch.setattr(tmaps.experiment.api, 'send_file', fake_method)
    url = '/api/channel_layers/{channel_layer_id}/tiles/{filename}'.format(
        filename=filename,
        channel_layer_id=layer.hash
    )
    res = rr.browser.get(url)

    assert res.status_code == 200, \
        'Mock return value did not work'

    fake_method.assert_called_once_with(p.join(layer.location, filename))

#
# GET FEATURES
#
def test_get_features_nologin(anybody, testexp, session):
    res = anybody.get('/api/experiments/{id}/features'.format(id=testexp.hash))
    assert res.status_code == 401


def test_get_features(rr, testexp, session):

    cells = MapobjectType(
        name='cells',
        experiment_id=testexp.id)
    nuclei = MapobjectType(
        name='nuclei',
        experiment_id=testexp.id)
    session.add_all([cells, nuclei])
    session.flush()

    session.add_all([
        Feature(name='CellArea', mapobject_type_id=cells.id),
        Feature(name='NucleusArea', mapobject_type_id=nuclei.id),
    ])

    session.commit()

    res = rr.browser.get('/api/experiments/{id}/features'.format(id=testexp.hash))

    assert res.status_code == 200, \
        'Function get_features did not return a successful response'

    resp = json.loads(res.data)

    assert resp['features']['cells'][0]['name'] == 'CellArea'
    assert resp['features']['nuclei'][0]['name'] == 'NucleusArea'
