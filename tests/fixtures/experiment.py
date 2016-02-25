import pytest
from tmaps.experiment import Experiment


@pytest.fixture(scope='function')
def testexp(request, testuser):
    exp = Experiment.create(
        name='Some experiment',
        description='Some desc',
        owner=testuser,
        microscope_type='visiview',
        plate_format=96
    )
    def teardown():
        exp.delete()
    request.addfinalizer(teardown)
    return exp

