from tmlib.models import User


def test_session_fixture_1(session):
    u = User(
        name='Random Test Dude',
        email='random@test.com', password='123')
    session.add(u)
    session.commit()


def test_session_fixture_2(session):
    u = session.query(User).filter_by(name='Random Test Dude').first()
    assert u is None, (
        'Objects added within a test function should be removed '
        'from the DB after the test ends.'
    )
