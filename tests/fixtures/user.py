import pytest
from tmaps.models import User


@pytest.fixture(scope='session')
def testuser(db):
    testuser = User.query.get(1)
    return testuser
