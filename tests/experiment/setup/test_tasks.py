# import pytest


# @pytest.mark.skipif(True, reason='Not implemented')
# def test_get_task_status_without_login(client):
#     resp = client.get('/api/experiments')
#     assert resp.status_code == 401


# @pytest.mark.skipif(True, reason='Not implemented')
# def test_get_task_status(authclient, testtask):
#     resp = authclient.get('/api/experiments/%d' % testtask.task_id)
#     assert resp.status_code == 200
