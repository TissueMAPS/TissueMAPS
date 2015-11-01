# import json
# from tests.conftest import login


# def test_get_appstates(db, client):
#     # Get app states when not logged in
#     rv = client.get('/appstates')
#     assert rv.status_code == 401

#     rv = client.post(
#         '/auth',
#         headers={'content-type': 'application/json'},
#         data=json.dumps({
#             'username': 'testuser',
#             'password': '123'
#         })
#     )

#     data = json.loads(rv.data)
#     assert 'token' in data

#     token = data['token']

#     rv = client.get('/appstates', headers={
#         'Authorization': 'Bearer ' + token
#     })
#     data = json.loads(rv.data)

#     assert rv.status_code == 200
#     assert 'owned' in data
#     assert 'shared' in data
