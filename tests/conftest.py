import json
import py.test as pytest
from models import *
from app import create_app
from app import db as _db

# TESTDB = 'test.db'
# TESTDB_PATH = "tests/{}".format(TESTDB)
# TEST_DATABASE_URI = 'sqlite:///' + TESTDB_PATH

@pytest.fixture(scope='session')
def app(request):
    """Session-wide test `Flask` application."""
    app = create_app(mode='test')

    # Establish an application context before running the tests.
    ctx = app.app_context()
    ctx.push()

    def teardown():
        ctx.pop()

    request.addfinalizer(teardown)
    return app

# @pytest.fixture(scope='module')
# def client_auth(app):
#     client = app.test_client()
#     rv = client.post(
#         '/auth',
#         headers={'content-type': 'application/json'},
#         data=json.dumps({
#             'username': 'testuser',
#             'password': '123'
#         })
#     )
#     data = json.loads(rv.data)
#     app.wsgi_app = LoginMiddleware(app, data['token'])
#     return client


@pytest.fixture(scope='module')
def client(app):
    # m = LoginMiddleware(app)
    return app.test_client()


@pytest.fixture(scope='session')
def db(app, request):
    """Session-wide test database."""

    _db.app = app
    _db.drop_all()
    _db.create_all()

    # Add some testing data
    u = User(name='testuser',
             email='testuser@something.com',
             password='123',
             expdatadir='/home/testuser')

    _db.session.add(u)
    _db.session.commit()

    return _db


@pytest.fixture(scope='function')
def dbsession(db, request):
    """Creates a new database session for a test."""
    connection = db.engine.connect()
    transaction = connection.begin()

    options = dict(bind=connection)
    session = db.create_scoped_session(options=options)

    db.session = session

    def teardown():
        transaction.rollback()
        connection.close()
        session.remove()

    request.addfinalizer(teardown)
    return session


def login(client):
    """Helper function to login"""
    rv = client.post(
        '/auth',
        headers={'content-type': 'application/json'},
        data=json.dumps({
            'username': 'testuser',
            'password': '123'
        })
    )
    data = json.loads(rv.data)
    token = data['token']
    wsgi = client.application.wsgi_app
    client.application.wsgi_app = LoginMiddleware(wsgi, token)
    return client


def register(client, username, password, email):
    """Helper function to register a user"""
    return client.post('/register', data={
        'username':     username,
        'password':     password,
        'email':        email,
    }, follow_redirects=True)


class LoginMiddleware(object):
    def __init__(self, app, token):
        self.app = app
        self.token = token

    def __call__(self, environ, start_response):

        def custom_start_response(status, headers, exc_info=None):
            headers.append(('Authorization', 'Bearer ' + self.token))
            print 'Send request with headers: ' + str(headers)
            return start_response(status, headers, exc_info)

        return self.app(environ, custom_start_response)
