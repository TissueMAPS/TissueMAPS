import pytest
from tmaps.experiment import Experiment


def _create_testexperiment(session, request, app, user,
                           name, microscope_type, plate_acquisition_mode,
                           plate_format, description=''):
    exp = Experiment(
        name=name,
        root_directory=app.config['TMAPS_STORAGE'],
        description=description,
        user_id=user.id,
        microscope_type=microscope_type,
        plate_acquisition_mode=plate_acquisition_mode,
        plate_format=plate_format
    )
    session.add(exp)
    session.commit()

    def teardown():
        session.delete(exp)
        session.commit()

    request.addfinalizer(teardown)
    return exp


@pytest.fixture(scope='function')
def testexps(Session, request, app, roborobin, tmpdir_factory):

    session = Session()

    cellvoyager_384_1plate_2acquisitions_multiplexing = _create_testexperiment(
        session=session, request=request, app=app,
        plate_acquisition_mode='multiplexing',
        name='Some experiment', user=roborobin,
        microscope_type='visiview', plate_format=96)

    return {
        'cellvoyager_384_1plate_2acquisitions_multiplexing':
            cellvoyager_384_1plate_2acquisitions_multiplexing
    }
