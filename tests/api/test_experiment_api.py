import pytest
import mock
import json
from tmaps.models import User


def test_get_experiments_without_login(client):
    resp = client.get('/api/experiments')
    assert resp.status_code == 401
    data = json.loads(resp.data)
    assert data['description'] == 'Request does not contain an access token'

def test_get_experiments_with_login(authclient):
    resp = authclient.get('/api/experiments')
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert 'owned' in data
    assert 'shared' in data
    assert type(data['owned']) == list
    assert type(data['shared']) == list

def test_get_single_experiment_without_login(client, testexp):
    resp = client.get('/api/experiments/' + testexp.hash)
    assert resp.status_code == 401

def test_get_single_experiment_with_login(authclient, testexp):
    resp = authclient.get('/api/experiments/' + testexp.hash)
    assert resp.status_code == 200
    serialized_exp = json.loads(resp.data)
    assert serialized_exp == testexp.as_dict()


experiment_request = {
    'name': 'Some experiment',
    'description': 'Some desc',
    'microscope_type': 'visiview',
    'plate_format': 96
}
experiment_request_json = json.dumps(experiment_request)

def test_create_experiment_without_login(client):
    resp = client.post(
        '/api/experiments',
        data=experiment_request_json
    )
    assert resp.status_code == 401

def test_create_experiment_with_login(authclient, testuser, db):
    resp = authclient.post(
        '/api/experiments',
        data=experiment_request_json
    )
    assert resp.status_code == 200

    # Check return value
    serialized_exp = json.loads(resp.data)
    assert serialized_exp['name'] == 'Some experiment'
    assert serialized_exp['description'] == 'Some desc'
    assert type(serialized_exp['id']) == unicode
    assert serialized_exp['microscope_type'] == 'visiview'
    assert serialized_exp['plate_format'] == 96
    assert 'layers' in serialized_exp
    assert 'plates' in serialized_exp
    assert 'plate_sources' in serialized_exp

    # Check if the experiment was added to the db correctly
    assert len(testuser.experiments) == 1
    exp = testuser.experiments[0]
    assert exp.name == experiment_request['name']

    # Delete the exp again
    exp.delete()


def test_delete_experiment(authclient, testuser, testexp, monkeypatch):
    fake_delete = mock.Mock()
    monkeypatch.setattr(testexp, 'delete', fake_delete)
    authclient.delete('/api/experiments/%s' % testexp.hash)
    fake_delete.assert_called_with()


def test_db(testuser):
    assert len(testuser.experiments) == 0

@pytest.mark.skipif(True, reason='Not implemented')
def test_create_layers():
    assert False
