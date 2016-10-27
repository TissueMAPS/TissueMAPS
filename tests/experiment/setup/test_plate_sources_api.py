# import mock
# import json
# import pytest
# from tmserver.models import PlateSource, PlateAcquisition


# def test_get_plate_sources_without_login(client, platesource):
#     resp = client.get(
#         '/api/experiments/%s/plate-sources' % platesource.experiment.hash)
#     assert resp.status_code == 401


# def test_get_plate_sources(authclient, platesource):
#     resp = authclient.get(
#         '/api/experiments/%s/plate-sources' % platesource.experiment.hash)

#     # Check HTTP answer
#     assert resp.status_code == 200
#     data = json.loads(resp.data)
#     assert 'plate_sources' in data

#     # Check payload data
#     serialized_pls = data['plate_sources'][0]
#     assert serialized_pls['id'] == platesource.id
#     assert serialized_pls['name'] == platesource.name
#     assert serialized_pls['description'] == platesource.description
#     assert serialized_pls['acquisitions'] == []


# def test_create_plate_source(authclient, testexp, monkeypatch):
#     # Monkeypatch the PlateSource object on the api module, not on tmaps,
#     # since it was already imported.
#     import tmserver.api.sources
#     pls_cls = mock.Mock(wraps=PlateSource)
#     monkeypatch.setattr(tmaps.api.sources, 'PlateSource', pls_cls)

#     request_payload = json.dumps({
#         'name': 'Some plate source'
#     })
#     resp = authclient.post(
#         '/api/experiments/%s/plate-sources' % testexp.hash,
#         data=request_payload)
#     # Check HTTP answer
#     assert resp.status_code == 200

#     # Check response
#     data = json.loads(resp.data)
#     assert data['name'] == 'Some plate source'
#     assert data['description'] == ''

#     # Check that the plate source was actually created
#     pls_cls.create.assert_called_with(
#         name='Some plate source', description='', experiment=testexp)


# def test_delete_plate_source(authclient, platesource, testexp):
#     # There should be one plate source before deletion
#     assert len(testexp.plate_sources) == 1

#     resp = authclient.delete(
#         '/api/plate-sources/%d' % platesource.id)

#     # Check HTTP answer
#     assert resp.status_code == 200

#     # The plate source should have been deleted
#     assert len(testexp.plate_sources) == 0



# def test_create_acquisition(authclient, platesource):
#     resp = authclient.post(
#         '/api/plate-sources/%s/acquisitions' % platesource.id,
#         data=json.dumps({
#             'name': 'Some acqu',
#             'description': 'Some desc'
#         })
#     )
#     # Check HTTP answer
#     assert resp.status_code == 200

#     data = json.loads(resp.data)

#     # Check payload data
#     assert len(platesource.acquisitions) == 1
#     aq = platesource.acquisitions[0]

#     assert data['id'] == aq.id
#     assert data['name'] == aq.name
#     assert data['description'] == aq.description
#     assert data['files'] == []
#     assert data['upload_status'] == 'WAITING'


# def test_delete_acquisition(authclient, acquisition, platesource):
#     # One acquisition should exist before removal
#     assert len(platesource.acquisitions) == 1

#     resp = authclient.delete(
#         '/api/acquisitions/%d' % acquisition.id)
#     # Check HTTP answer
#     assert resp.status_code == 200

#     assert len(platesource.acquisitions) == 0
