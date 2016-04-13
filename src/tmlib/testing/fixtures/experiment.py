import pytest
from tmlib.models import Experiment, Channel, ChannelLayer, MapobjectType


@pytest.yield_fixture(scope='function')
def testexps(session, request, config, roborobin, tmpdir_factory):
    #
    # Declare all test experiments.
    #

    # (1) Add cellvoyager experiment
    cellvoyager_384_1plate_2acquisitions_multiplexing = Experiment(
        name='Cellvoyager_384',
        user_id=roborobin.id,
        plate_acquisition_mode='multiplexing',
        root_directory=config['TMAPS_STORAGE'],
        microscope_type='visiview',
        plate_format=96
    )
    session.add(cellvoyager_384_1plate_2acquisitions_multiplexing)
    session.flush()
    # Add channels
    experiment_1_channel_1 = \
        Channel(
            name='Channel_01',
            index=1,
            experiment_id=cellvoyager_384_1plate_2acquisitions_multiplexing.id
        )
    session.add(experiment_1_channel_1)
    session.flush()
    # Add channel layers
    experiment_1_channel_1_layers = [
        ChannelLayer(
            tpoint=0,
            zplane=0,
            channel_id=experiment_1_channel_1.id)
    ]
    session.add_all(
        experiment_1_channel_1_layers)
    session.flush()

    session.commit()

    # Yield them in a dict so they can be easily accessed by the consumer of
    # the fixture.
    test_experiments = {
        'cellvoyager_384_1plate_2acquisitions_multiplexing':
            cellvoyager_384_1plate_2acquisitions_multiplexing
    }

    yield test_experiments

    for e in test_experiments.values():
        session.delete(e)
    session.commit()

