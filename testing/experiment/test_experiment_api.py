import uuid
import os.path as p
import os
import pytest
import numpy as np
import mock
import json
import tmaps
from tmaps.experiment import Experiment


@pytest.fixture
def testexp(testexps):
    """Choose a single experiment for the experiment rest API unit tests."""
    return testexps['cellvoyager_384_1plate_2acquisitions_multiplexing']


def test_get_experiments_without_login(anybody):
    resp = anybody.get('/api/experiments')
    assert resp.status_code == 401


def test_get_experiments_with_login(rr):
    resp = rr.browser.get('/api/experiments')
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert 'experiments' in data


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


def test_delete_experiment(rr, testexp, monkeypatch, session):
    # monkeypatch.setattr(db.session, 'delete', fake_delete)
    assert session.query(Experiment).get(testexp.id) is not None, \
        'Test experiment of fixture not present in database'
    response = rr.browser.delete('/api/experiments/%s' % testexp.hash)
    assert response.status_code == 200
    assert session.query(Experiment).get(testexp.id) is None, \
        'Experiment was not successfully deleted after DELETE request'
