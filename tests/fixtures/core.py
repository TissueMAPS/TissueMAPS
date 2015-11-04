import os.path as p
import json

import flask
import pytest

import tmaps
from tmaps.models import User
from tmaps.appfactory import create_app
from tmaps.extensions.database import db as _db


@pytest.fixture(scope='session')
def app(request):
    """Session-wide test `Flask` application."""

    cfg = flask.Config(p.join(p.dirname(tmaps.__file__), p.pardir))
    cfg.from_envvar('TMAPS_SETTINGS_TEST')
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

    with app.app_context():
        # Add some testing data
        userdir = str(tmpdir_factory.mktemp('testuser'))
        u = User(name='testuser',
                 email='testuser@something.com',
                 location=userdir,
                 password='123')
        _db.session.add(u)
        _db.session.commit()

    def teardown():
        # Commit before dropping, otherwise pytest will hang!
        # _db.session.commit()
        # _db.drop_all()
        pass
    request.addfinalizer(teardown)

    return _db


@pytest.fixture(scope='module')
def authclient(app):
    client = app.test_client()

    rv = client.post(
        '/auth',
        headers={'content-type': 'application/json'},
        data=json.dumps({
            'username': 'testuser',
            'password': '123'
        })
    )
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
def client(app):
    # m = LoginMiddleware(app)
    return app.test_client()
