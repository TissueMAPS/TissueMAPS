import pytest
from tmaps.user import User


def _teardown_func(session, user):
    """Create a function that can be used as a finalizer
    to delete a user object from the db."""
    def teardown():
        session.delete(user)
        session.commit()
    return teardown


@pytest.fixture(scope='session')
def roborobin(Session, request, tmpdir_factory):
    session = Session()

    u = User(
        name='Robo Robin',
        email='roborobin@testing.com',
        password='123')

    session.add(u)
    session.commit()

    request.addfinalizer(_teardown_func(session, u))

    return u


@pytest.fixture(scope='session')
def robomarkus(Session, request, tmpdir_factory):
    session = Session()

    u = User(
        name='Robo Markus',
        email='robomarkus@testing.com',
        password='123')

    session.add(u)
    session.commit()

    request.addfinalizer(_teardown_func(session, u))
    return u
