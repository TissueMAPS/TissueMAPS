import pytest
from tmaps.user import User


def _teardown_func(db, user):
    """Create a function that can be used as a finalizer
    to delete a user object from the db."""
    def teardown():
        db.session.delete(user)
        db.session.commit()
    return teardown


@pytest.fixture(scope='session')
def roborobin(app, db, request, tmpdir_factory):
    u = User(
        name='Robo Robin',
        email='roborobin@testing.com',
        password='123')
    db.session.add(u)
    db.session.commit()

    request.addfinalizer(_teardown_func(db, u))

    return u


@pytest.fixture(scope='session')
def robomarkus(db, request, tmpdir_factory):
    u = User(
        name='Robo Markus',
        email='robomarkus@testing.com',
        password='123')
    db.session.add(u)
    db.session.commit()

    request.addfinalizer(_teardown_func(db, u))
    return u
