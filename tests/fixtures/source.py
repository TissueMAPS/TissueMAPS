import pytest
from tmaps.experiment.setup import PlateSource, PlateAcquisition


@pytest.fixture
def platesource(testexp):
    pls = PlateSource.create(name='Some source', experiment=testexp)
    return pls


@pytest.fixture
def acquisition(platesource):
    aq = PlateAcquisition.create(name='Some source', plate_source=platesource)
    return aq
