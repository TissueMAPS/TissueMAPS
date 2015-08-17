from models import *

def test_db_population_before_testing(dbsession):
    user = User.query.filter_by(name='testuser').first()
    assert user.name == 'testuser'
