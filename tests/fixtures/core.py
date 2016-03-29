import os.path as p
import json

import flask
import pytest

import tmaps
from tmaps.appfactory import create_app
from tmaps.extensions import db as _db
from tmaps.model import Model


class Client(object):
    """Simple container for a user object and a Werkzeug test client
    whose requests are authenticated with the user's credentials."""
    def __init__(self, user, browser):
        self.user = user
        self.browser = browser


@pytest.fixture(scope='session')
def app(request, tmpdir_factory):
    """Session-wide test `Flask` application."""

    cfg = flask.Config(p.join(p.dirname(tmaps.__file__), p.pardir))
    cfg.from_envvar('TMAPS_SETTINGS_TEST')


    cfg['GC3PIE_SESSION_DIR'] = str(tmpdir_factory.mktemp('gc3pie'))
    cfg['TMAPS_STORAGE'] = str(tmpdir_factory.mktemp('experiments'))

    app = create_app(cfg)

    # Establish an application context before running the tests.
    ctx = app.app_context()
    ctx.push()

    # Called when last test in scope has finished
    def teardown():
        ctx.pop()
    request.addfinalizer(teardown)

    return app


@pytest.fixture(scope='session', autouse=True)
def db(app, request):
    """The Flask-SQLAlchemy database fixture.

    This fixture will be created once for the whole test session.
    On the first use it will create the database schema of tmlib and tmserver.

    """
    # Initialize testing database
    _db.app = app
    # Commit before dropping, otherwise pytest might hang!
    _db.session.close()
    Model.metadata.drop_all(_db.engine)
    _db.create_all()

    Model.metadata.create_all(_db.engine)

    def teardown():
        # Commit before dropping, otherwise pytest will hang!
        _db.session.close()
        Model.metadata.drop_all(_db.engine)

    request.addfinalizer(teardown)

    return _db


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


@pytest.fixture(scope='module')
def rr(app, roborobin):
    """An object of type Client that contains a test client authenticated
    with the credentials of user Robo Robin."""
    browser = make_test_client(app, roborobin, '123')
    return Client(user=roborobin, browser=browser)


@pytest.fixture(scope='module')
def rm(app, robomarkus):
    """An object of type Client that contains a test client authenticated
    with the credentials of user Robo Markus."""
    browser = make_test_client(app, robomarkus, '123')
    return Client(user=robomarkus, browser=browser)

@pytest.fixture(scope='module')
def anybody(app):
    """A non-authenticated test client"""
    return app.test_client()
