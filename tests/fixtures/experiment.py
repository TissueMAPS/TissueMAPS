import pytest
from tmaps.experiment import Experiment


def _create_testexperiment(db, request, app, user,
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
    db.session.add(exp)
    db.session.commit()

    def teardown():
        db.session.delete(exp)
        db.session.commit()

    request.addfinalizer(teardown)
    return exp


@pytest.fixture(scope='function')
def testexps(db, request, app, roborobin, tmpdir_factory):
    cellvoyager_384_1plate_2acquisitions_multiplexing = _create_testexperiment(
        db=db, request=request, app=app,
        plate_acquisition_mode='multiplexing',
        name='Some experiment', user=roborobin,
        microscope_type='visiview', plate_format=96)

    return {
        'cellvoyager_384_1plate_2acquisitions_multiplexing':
            cellvoyager_384_1plate_2acquisitions_multiplexing
    }
