import pytest
from tmaps.models import User


@pytest.fixture(scope='session')
def testuser(app, db, request, tmpdir_factory):
    userdir = str(tmpdir_factory.mktemp('testuser'))

    u = User.create(
        name='testuser',
        email='testuser@someprovder.com',
        location=userdir,
        password='123')

    request.addfinalizer(lambda: u.delete())

    return u


@pytest.fixture(scope='session')
def testuser2(db, request, tmpdir_factory):
    userdir = str(tmpdir_factory.mktemp('testuser2'))

    u = User.create(
        name='testuser2',
        email='testuser@somethingelse.com',
        location=userdir,
        password='123')

    request.addfinalizer(lambda: u.delete())

    return u
