import os.path as p
import json

import flask
import pytest

import tmaps
from tmaps.appfactory import create_app
from tmaps.extensions import db as _db
from tmaps.model import Model


@pytest.yield_fixture(scope='session', autouse=True)
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

    yield app

    ctx.pop()


@pytest.yield_fixture(scope='session', autouse=True)
def db(app, engine, request):
    """The Flask-SQLAlchemy database fixture.

    This fixture will be created once for the whole test session.
    On the first use it will create the database schema of tmlib and tmserver.

    """
    ## Initialize testing database
    _db.app = app
    # Close before dropping, otherwise pytest might hang!
    _db.session.close()
    # Recreate tables
    Model.metadata.drop_all(engine)
    Model.metadata.create_all(engine)

    yield _db

    # Close before dropping, otherwise pytest might hang!
    _db.session.close()
    # Drop all tables again
    Model.metadata.drop_all(engine)


@pytest.fixture(scope='function', autouse=True)
def dbsession(db, session, monkeypatch):
    """Monkeypatch the session on the Flask-SqlAlchemy object
    to correspond to the session fixture of the test app."""
    monkeypatch.setattr(db, 'session', session)

