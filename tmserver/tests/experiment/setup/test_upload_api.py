# import os
# import os.path as p
# import pytest
# import fakeredis
# import json
# from StringIO import StringIO


# @pytest.fixture
# def redis_store(monkeypatch):
#     import tmserver.api.upload
#     redis = fakeredis.FakeRedis()
#     # Important: the object needs to be replaced on the api module
#     # directly, not on in the module where it is originally defined!
#     monkeypatch.setattr(tmaps.api.upload, 'redis_store', redis)
#     return redis


# register_payload = json.dumps({
#     'files': [
#         'file1',
#         'file2'
#     ]
# })


# def test_register_upload_without_login(client, acquisition):
#     resp = client.put(
#         '/api/acquisitions/%d/register-upload' % acquisition.id,
#         data=register_payload)
#     assert resp.status_code == 401


# def test_register_upload_with_bogus_acquisition(authclient):
#     resp = authclient.put(
#         '/api/acquisitions/%d/register-upload' % 123123,
#         data=register_payload)
#     assert resp.status_code == 404


# def test_register_upload_with_malformed_request(authclient, acquisition):
#     # There has to be a file array
#     resp = authclient.put(
#         '/api/acquisitions/%d/register-upload' % acquisition.id,
#         data=json.dumps({}))
#     assert resp.status_code == 400

#     # An empty file array is a malformed request
#     resp = authclient.put(
#         '/api/acquisitions/%d/register-upload' % acquisition.id,
#         data=json.dumps({
#             'files': []
#     }))
#     assert resp.status_code == 400


# def test_register_upload(authclient, acquisition, redis_store):
#     resp = authclient.put(
#         '/api/acquisitions/%d/register-upload' % acquisition.id,
#         data=register_payload)
#     assert resp.status_code == 200

#     file_key = 'acquisition:%d:upload:files' % acquisition.id
#     registered_flag_key = 'acquisition:%d:upload:registered' % acquisition.id

#     assert redis_store.get(registered_flag_key) == 'True'
#     assert redis_store.smembers(file_key) == set(['file1', 'file2'])


# def test_upload_file_without_login(client, acquisition):
#     resp = client.post(
#         '/api/acquisitions/%d/upload-file' % acquisition.id)
#     assert resp.status_code == 401


# def test_upload_file_without_registering(authclient, acquisition):
#     resp = authclient.post(
#         '/api/acquisitions/%d/upload-file' % acquisition.id,
#         data={
#             'file': (StringIO('file1 content'), 'file1.png')
#         })
#     assert resp.status_code == 400


# def _register_files(filenames, authclient, acquisition):
#     """Helper method to register files"""
#     resp = authclient.put(
#         '/api/acquisitions/%d/register-upload' % acquisition.id,
#         data=json.dumps({'files': filenames})
#     )
#     return resp


# def test_upload_file_with_registering(authclient, acquisition, redis_store):
#     # Acquisition starts in WAITING status
#     assert acquisition.upload_status == 'WAITING'

#     resp = _register_files(
#         ['file1.png', 'file2.png'], authclient, acquisition)
#     assert resp.status_code == 200

#     # Start uploading
#     resp = authclient.post(
#         '/api/acquisitions/%d/upload-file' % acquisition.id,
#         data={'file': (StringIO('file1 content'), 'file1.png')})
#     assert resp.status_code == 200
#     assert p.exists(p.join(acquisition.images_location, 'file1.png' ))

#     # One file remains
#     assert acquisition.upload_status == 'UPLOADING'

#     resp = authclient.post(
#         '/api/acquisitions/%d/upload-file' % acquisition.id,
#         data={'file': (StringIO('file2 content'), 'file2.png')})
#     assert resp.status_code == 200
#     assert p.exists(p.join(acquisition.images_location, 'file2.png' ))

#     # All files uploaded, status should be SUCCESSFUL
#     assert acquisition.upload_status == 'SUCCESSFUL'

#     # Before doing a new upload, there are 2 files in the dir.
#     assert len(os.listdir(acquisition.images_location)) == 2

#     # Registering a new upload should reset the status
#     # and delete all files.
#     resp = _register_files(
#         ['file3.png'], authclient, acquisition)

#     assert acquisition.upload_status == 'WAITING'
#     assert len(os.listdir(acquisition.images_location)) == 0
