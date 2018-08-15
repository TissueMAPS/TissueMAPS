import os.path as p
import os
import sys
import json

import flask
import pytest

import tmserver
from tmserver.appfactory import create_app
from tmserver.extensions import db as _db
from tmserver.model import Model


@pytest.yield_fixture(scope='session', autouse=True)
def app(request, tmpdir_factory):
    """Session-wide test `Flask` application."""

    cfg = flask.Config(p.join(p.dirname(tmaps.__file__), p.pardir))

    if not 'TMAPS_SETTINGS_TEST' in os.environ:
        print (
            'No test config specified by the environment variable'
            ' `TMAPS_SETTINGS_TEST`! Make sure that this config'
            ' exists and that it specifies a database different'
            ' from the one used normally! The database will be wiped'
            ' during testing!'
        )
        sys.exit(1)
    else:
        print (
            'Loading server config from: %s' % os.environ['TMAPS_SETTINGS_TEST']
        )
        cfg.from_envvar('TMAPS_SETTINGS_TEST')

    cfg['GC3PIE_SESSION_DIR'] = str(tmpdir_factory.mktemp('gc3pie'))
    cfg['TMAPS_STORAGE'] = str(tmpdir_factory.mktemp('experiments'))

    app = create_app(config_overrides=cfg)

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
    engine.dispose()
    # Drop all tables again
    Model.metadata.drop_all(engine)


@pytest.fixture(scope='function', autouse=True)
def dbsession(db, session, monkeypatch):
    """Monkeypatch the session on the Flask-SqlAlchemy object
    to correspond to the session fixture of the test app."""
    monkeypatch.setattr(db, 'session', session)
