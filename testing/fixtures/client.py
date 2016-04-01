import json

import pytest


class Client(object):
    """Simple container for a user object and a Werkzeug test client
    whose requests are authenticated with the user's credentials."""
    def __init__(self, user, browser):
        self.user = user
        self.browser = browser


def make_test_client(app, user, password):
    """Helper function to create a werkzeug test client.
    The test client is monkey patched in such a way that it will send
    the authentication header with each request."""

    client = app.test_client()
    rv = client.post(
        '/auth',
        headers={'content-type': 'application/json'},
        data=json.dumps({
            'username': user.name,
            'password': password
        })
    )
    assert rv.status_code == 200
    data = json.loads(rv.data)
    token = data['access_token']

    for method in ['get', 'post', 'put', 'delete']:
        def gen_authed_meth():
            old_method = getattr(client, method)
            def authed_meth(*args, **kwargs):
                headers = kwargs.get('headers', [])
                headers.append(('Authorization', 'JWT %s' % token))
                kwargs['headers'] = headers
                return old_method(*args, **kwargs)
            return authed_meth
        setattr(client, method, gen_authed_meth())

    return client


@pytest.fixture(scope='session')
def rr(app, roborobin):
    """An object of type Client that contains a test client authenticated
    with the credentials of user Robo Robin."""
    browser = make_test_client(app, roborobin, '123')
    return Client(user=roborobin, browser=browser)


@pytest.fixture(scope='session')
def rm(app, robomarkus):
    """An object of type Client that contains a test client authenticated
    with the credentials of user Robo Markus."""
    browser = make_test_client(app, robomarkus, '123')
    return Client(user=robomarkus, browser=browser)


@pytest.fixture(scope='module')
def anybody(app):
    """A non-authenticated test client"""
    return app.test_client()
