import pytest
from tmlib.models import User


# def _teardown_func(session, user):
#     """Create a function that can be used as a finalizer
#     to delete a user object from the db."""
#     def teardown():
#         print 'FINALIZER CALLED'
#         session.delete(user)
#         session.commit()
#     return teardown


@pytest.fixture(scope='session')
def roborobin(persistent_session, request):
    # session = Session()

    u = User(
        name='Robo Robin',
        email='roborobin@testing.com',
        password='123')

    # request.addfinalizer(_teardown_func(session, u))

    persistent_session.add(u)
    persistent_session.commit()

    return u


@pytest.fixture(scope='session')
def robomarkus(persistent_session):
    u = User(
        name='Robo Markus',
        email='robomarkus@testing.com',
        password='123')

    persistent_session.add(u)
    persistent_session.commit()

    return u
