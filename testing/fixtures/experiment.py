import pytest


@pytest.fixture(scope='function')
def testexp(testexps):
    """Choose a single experiment for the experiment rest API unit tests."""
    return testexps['cellvoyager_384_1plate_2acquisitions_multiplexing']
