import pytest
from tmlib.models import Experiment


def _create_testexperiment(session, request, config, user,
                           name, microscope_type, plate_acquisition_mode,
                           plate_format, description=''):
    exp = Experiment(
        name=name,
        root_directory=config['TMAPS_STORAGE'],
        description=description,
        user_id=user.id,
        microscope_type=microscope_type,
        plate_acquisition_mode=plate_acquisition_mode,
        plate_format=plate_format
    )

    session.add(exp)
    session.commit()

    return exp


@pytest.yield_fixture(scope='function')
def testexps(session, request, config, roborobin, tmpdir_factory):

    # Declare all test experiments.
    cellvoyager_384_1plate_2acquisitions_multiplexing = _create_testexperiment(
        session=session, request=request,
        plate_acquisition_mode='multiplexing', config=config,
        name='Cellvoyager_384', user=roborobin,
        microscope_type='visiview', plate_format=96)

    # Yield them in a dict so they can be easily accessed by the consumer of
    # the fixture.
    test_experiments = {
        'cellvoyager_384_1plate_2acquisitions_multiplexing':
            cellvoyager_384_1plate_2acquisitions_multiplexing
    }

    yield test_experiments
