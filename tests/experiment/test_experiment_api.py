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


@pytest.mark.skipif(True, reason='Not implemented')
def test_experiment_shares(rr):
    pass


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


experiment_request = {
    'name': 'Some experiment',
    'description': 'Some desc',
    'microscope_type': 'visiview',
    'plate_acquisition_mode': 'multiplexing',
    'plate_format': 96
}
experiment_request_json = json.dumps(experiment_request)


def test_create_experiment_without_login(anybody):
    resp = anybody.post(
        '/api/experiments',
        data=experiment_request_json
    )
    assert resp.status_code == 401


def test_create_experiment_with_login(rr, db, monkeypatch):
    resp = rr.browser.post(
        '/api/experiments',
        data=experiment_request_json
    )
    assert resp.status_code == 200

    # Check return value
    resp = json.loads(resp.data)
    assert 'experiment' in resp
    serialized_exp = resp['experiment']

    # Check if the experiment was added to the db correctly
    assert rr.user.experiments[0].name == experiment_request['name']

    # Check if the returned experiment is the same as the added one
    e = db.session.query(Experiment).get_with_hash(serialized_exp['id'])
    assert e.hash == serialized_exp['id']

    # Delete the exp again
    db.session.delete(e)
    db.session.commit()


# def test_delete_experiment(db, rr, testexp, monkeypatch):
#     fake_delete = mock.Mock()
#     monkeypatch.setattr(db.session, 'delete', fake_delete)
#     rr.browser.delete('/api/experiments/%s' % testexp.hash)
#     fake_delete.assert_called_with()


@pytest.mark.skipif(True, reason='Not implemented')
def test_create_layers():
    assert False


@pytest.mark.skipif(True, reason='Not implemented')
def test_expdata_file_without_login(anybody):
    pass


@pytest.mark.skipif(True, reason='Not implemented')
def test_get_features_without_login(anybody):
    pass


@pytest.mark.skipif(True, reason='Not implemented')
def test_get_features(rr):
    pass


# @pytest.mark.skipif(True, reason='Not implemented')
# def test_get_objects(rr, testexp):

#     def create_object(typenames):
#         import h5py
#         filename = p.join(cellvoyager_384_1plate_2acquisitions_multiplexing.location, 'data.h5')
#         f = h5py.File(filename, 'w')
#         for t in typenames:
#             g = f.create_group('/objects/%s' % t)
#             g.attrs['visual_type'] = 'polygon'

#             g['ids'] = np.array([1, 2])
#             g['map_data/coordinates/1'] = np.array([[0, 0], [0, 1]])
#             g['map_data/coordinates/2'] = np.array([[0, 0], [0, 1]])
#         f.close()
#         return filename

#     filename = create_object(['cells', 'nuclei'])

#     resp = rr.browser.get('/api/experiments/%s/objects' % cellvoyager_384_1plate_2acquisitions_multiplexing.hash)
#     data = json.loads(resp.data)

#     assert 'cells' in data['objects']
#     assert 'nuclei' in data['objects']
#     assert data['objects']['cells']['map_data']['coordinates']['1'] == [[0, 0], [0, 1]]

#     os.remove(filename)


# @pytest.mark.skipif(True, reason='Throws error')
# def test_convert_images_api(rr.browser,
#         cellvoyager_384_1plate_2acquisitions_multiplexing, rm.browser, anybody):
#     options = {
#         'metaconfig': {
#             'file_format': 'default',
#             'z_stacks': False,
#             'regex': 'asf',
#             'stitch_layout': 'zigzag_horizontal',
#             'stitch_major_axis': 'vertical',
#             'stitch_horizontal': 10,
#             'stitch_vertical': 10
#         },
#         'imextract': {
#             'batch_size': 10
#         }
#     }

#     def request(cl, expid, options=options):
#         rv = cl.post(
#             '/api/experiments/%s/convert-images' % expid,
#             data=json.dumps(options))
#         return rv

#     rv = request(rr.browser, 'bogus_expid')
#     assert rv.status_code == 404

#     rv = request(rm.browser, cellvoyager_384_1plate_2acquisitions_multiplexing.hash)
#     assert rv.status_code == 401

#     rv = request(anybody, 'bogus_expid')
#     assert rv.status_code == 401

#     # rv = request(rr.browser, cellvoyager_384_1plate_2acquisitions_multiplexing.hash)
#     # assert rv.status_code == 400

#     cellvoyager_384_1plate_2acquisitions_multiplexing.update(creation_stage='WAITING_FOR_IMAGE_CONVERSION')
#     rv = request(rr.browser, cellvoyager_384_1plate_2acquisitions_multiplexing.hash)
#     assert rv.status_code == 200
#     assert rv.content_type == 'application/json'

#     data = json.loads(resp.data)




