import sqlalchemy
import pytest

from tmlib.models import Model
from sqlalchemy.orm import sessionmaker


@pytest.fixture(scope='session')
def config(tmpdir_factory):
    """Session-wide test `Flask` application."""

    cfg = {}
    cfg['GC3PIE_SESSION_DIR'] = str(tmpdir_factory.mktemp('gc3pie'))
    cfg['TMAPS_STORAGE'] = str(tmpdir_factory.mktemp('experiments'))
    cfg['POSTGRES_DATABASE_URI'] = \
        'postgresql://{user}:{passw}@{host}:{port}/{dbname}'.format(
            user='robin', passw='phelot95', host='localhost',
            port=5432, dbname='tissuemaps_test')

    return cfg


@pytest.fixture(scope='session', autouse=True)
def engine(config, request):

    engine = sqlalchemy.create_engine(config['POSTGRES_DATABASE_URI'])
    Model.metadata.create_all(engine)

    def teardown():
        # Commit before dropping, otherwise pytest will hang!
        Model.metadata.drop_all(engine)

    request.addfinalizer(teardown)

    return engine


@pytest.fixture(scope='session')
def Session(engine):
    return sessionmaker(bind=engine)


@pytest.yield_fixture
def session(Session):
    session = Session()
    session.begin_nested()
    try:
        yield session
    finally:
        session.rollback()
