import os.path as p
import json

import flask
import pytest

import tmaps
from tmaps.user import User
from tmaps.appfactory import create_app
from tmaps.extensions.database import db as _db


@pytest.fixture(scope='session')
def app(request, tmpdir_factory):
    """Session-wide test `Flask` application."""

    cfg = flask.Config(p.join(p.dirname(tmaps.__file__), p.pardir))
    cfg.from_envvar('TMAPS_SETTINGS_TEST')
    cfg['GC3PIE_SESSION_DIR'] = str(tmpdir_factory.mktemp('gc3pie'))
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
def db(app, tmpdir_factory, request):
    # Initialize testing database
    _db.app = app
    # Commit before dropping, otherwise pytest might hang!
    _db.session.commit()
    _db.drop_all()
    _db.create_all()

    def teardown():
        # Commit before dropping, otherwise pytest will hang!
        # _db.session.commit()
        # _db.drop_all()
        pass
    request.addfinalizer(teardown)

    return _db


def make_test_client(app, user, password):
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
def authclient(app, testuser):
    cl = make_test_client(app, testuser, '123')
    return cl


@pytest.fixture(scope='module')
def authclient2(app, testuser2):
    cl = make_test_client(app, testuser2, '123')
    return cl


@pytest.fixture(scope='module')
def client(app):
    # m = LoginMiddleware(app)
    return app.test_client()
