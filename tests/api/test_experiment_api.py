import os.path as p
import pytest
import numpy as np
import mock
import json
from tmaps.models import User



def test_get_experiments_without_login(client):
    resp = client.get('/api/experiments')
    assert resp.status_code == 401

def test_get_experiments_with_login(authclient):
    resp = authclient.get('/api/experiments')
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert 'owned' in data
    assert 'shared' in data
    assert type(data['owned']) == list
    assert type(data['shared']) == list

@pytest.mark.skipif(True, reason='Not implemented')
def test_experiment_shares(authclient):
    pass



def test_get_single_experiment_without_login(client, testexp):
    resp = client.get('/api/experiments/' + testexp.hash)
    assert resp.status_code == 401, \
        'An experiment should only be requestable by logged in users'

def test_get_single_experiment_with_login(authclient, authclient2, testexp):
    # Test the case where the user has access to the experiment
    resp = authclient.get('/api/experiments/' + testexp.hash)
    assert resp.status_code == 200, \
        'A user should be able to GET his own experiments.'

    serialized_exp = json.loads(resp.data)
    assert serialized_exp == testexp.as_dict(), \
        'The returned experiment should be created by as_dict'


    resp = authclient.get('/api/experiments/' + 'bogus_hash')
    assert resp.status_code == 404, \
        'If no experiment can be found, a 404 response should be sent'

    resp = authclient2.get('/api/experiments/' + testexp.hash)
    assert resp.status_code == 401, \
        'An experiment should only be accessable its owner'


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


@pytest.mark.skipif(True, reason='Not implemented')
def test_expdata_file_without_login(client):
    pass


@pytest.mark.skipif(True, reason='Not implemented')
def test_get_features_without_login(client):
    pass


@pytest.mark.skipif(True, reason='Not implemented')
def test_get_features(authclient):
    pass


def test_get_objects(authclient, testexp):

    def create_object(typenames):
        import h5py
        f = h5py.File(p.join(testexp.location, 'data.h5'), 'w')
        for t in typenames:
            f.create_group('/objects/%s' % t)
            objs = f['/objects/%s' % t]
            objs['1'] = np.array([[0, 0], [0, 1]])
            objs['2'] = np.array([[0, 0], [0, 1]])
        f.close()

    create_object(['cells', 'nuclei'])

    resp = authclient.get('/api/experiments/%s/objects?types' % testexp.hash)
    data = json.loads(resp.data)
    assert 'types' in data
    assert data['types'] == ['cells', 'nuclei']

    resp = authclient.get('/api/experiments/%s/objects?objects' % testexp.hash)
    data = json.loads(resp.data)
    assert 'objects' in data
    assert data['objects']['cells']['1'] == [[0, 0], [0, 1]]

    # Both at the same time
    resp = authclient.get('/api/experiments/%s/objects?types&objects' % testexp.hash)
    data = json.loads(resp.data)
    assert 'objects' in data
    assert 'types' in data


@pytest.mark.skipif(True, reason='Throws error')
def test_convert_images_api(authclient, testexp, authclient2, client):
    options = {
        'metaconfig': {
            'file_format': 'default',
            'z_stacks': False,
            'regex': 'asf',
            'stitch_layout': 'zigzag_horizontal',
            'stitch_major_axis': 'vertical',
            'stitch_horizontal': 10,
            'stitch_vertical': 10
        },
        'imextract': {
            'batch_size': 10
        }
    }

    def request(cl, expid, options=options):
        rv = cl.post(
            '/api/experiments/%s/convert-images' % expid,
            data=json.dumps(options))
        return rv

    rv = request(authclient, 'bogus_expid')
    assert rv.status_code == 404

    rv = request(authclient2, testexp.hash)
    assert rv.status_code == 401

    rv = request(client, 'bogus_expid')
    assert rv.status_code == 401

    # rv = request(authclient, testexp.hash)
    # assert rv.status_code == 400

    testexp.update(creation_stage='WAITING_FOR_IMAGE_CONVERSION')
    rv = request(authclient, testexp.hash)
    assert rv.status_code == 200
    assert rv.content_type == 'application/json'

    data = json.loads(resp.data)




