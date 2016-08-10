import requests
import json
import inspect
import logging

from tmlib.utils import same_docstring_as

from tmclient.base import HttpClient

logger = logging.getLogger(__name__)


class ExperimentService(HttpClient):

    '''Class for querying a TissueMAPS experiment via RESTful API.'''

    @same_docstring_as(HttpClient.__init__)
    def __init__(self, hostname):
        super(ExperimentService, self).__init__(hostname)

    def __call__(self, cli_args):
        '''Calls a method with the provided keyword arguments.

        Paramaters
        ----------
        cli_args: argparse.Namespace
            parsed command line arguments that should be passed on to the
            specified method (appropriate arguments get automatically stripped)

        Raises
        ------
        AttributeError
            when `cli_args` don't have an attribute "method" that specifies
            the method that should be called or when the class doesn't have the
            specied method
        '''
        if not hasattr(cli_args, 'method'):
            raise AttributeError('Arguments must specify "method".')
        method_name = cli_args.method
        if not hasattr(self, method_name):
            raise AttributeError(
                'Object of type "%s" doesn\'t have a method "%s"'
                % (self.__class__.__name__, method_name)
            )
        args = vars(cli_args)
        method = getattr(self, method_name)
        kwargs = dict()
        valid_arg_names = inspect.getargspec(method).args
        for arg_name, arg_value in args.iteritems():
            if arg_name in valid_arg_names:
                kwargs[arg_name] = arg_value
        method(**kwargs)

    def get_experiment_id(self, experiment_name):
        '''Gets the ID of an :py:class:`tmlib.models.Experiment` given its name.

        Parameters
        ----------
        experiment_name: str
            name of the experiment

        Returns
        -------
        str
            experiment ID
        '''
        logger.debug('get ID for experiment "%s"', experiment_name)
        params = {
            'experiment_name': experiment_name,
        }
        url = self.build_url('/api/experiments/id', params)
        res = self.session.get(url)
        self._handle_error(res)
        return res.json()['id']

    def create_experiment(self, experiment_name, microscope_type,
            plate_format, plate_acquisition_mode):
        '''Creates a new :py:class:`tmlib.models.Experiment`.

        Parameters
        ----------
        experiment_name: str
            name that should be given to the experiment
        microscope_type: str
            microscope_type
        plate_format: int
            well-plate format, i.e. total number of wells per plate
        plate_acquisition_mode: str
            mode of image acquisition that determines whether acquisitions will
            be interpreted as time points as part of a time series experiment
            or as multiplexing cycles as part of a serial multiplexing
            experiment
        '''
        logger.info('create experiment "%s"', experiment_name)
        data = {
            'name': experiment_name,
            'microscope_type': microscope_type,
            'plate_format': plate_format,
            'plate_acquisition_mode': plate_acquisition_mode
        }
        url = self.build_url('/api/experiments')
        res = self.session.post(url, json=data)
        self._handle_error(res)

    def get_plate_id(self, experiment_id, plate_name):
        '''Gets the ID of a :py:class:`tmlib.models.Plate` given its name and
        the ID of the parent :py:class:`tmlib.models.Experiment`.

        Parameters
        ----------
        experiment_id: str
            ID of the parent experiment
        plate_name: str
            name of the plate

        Returns
        -------
        str
            plate ID
        '''
        logger.debug(
            'get plate ID given plate "%s" and experiment "%s"',
            plate_name, experiment_name
        )
        params = {
            'plate_name': plate_name,
        }
        url = self.build_url(
            '/api/experiments/%s/plates/id' % experiment_id, params
        )
        res = self.session.get(url)
        self._handle_error(res)
        return res.json()['id']

    def create_plate(self, experiment_id, plate_name):
        '''Creates a new :py:class:`tmlib.models.Plate`.

        Parameters
        ----------
        experiment_id: str
            ID of the parent experiment
        plate_name: str
            name that should be given to the plate
        '''
        logger.info(
            'create plate "%s" for experiment %s', plate_name, experiment_id
        )
        data = {
            'name': plate_name,
        }
        url = self.build_url('/api/experiments/%s/plates' % experiment_id)
        res = self.session.post(url, json=data)
        self._handle_error(res)

    def get_acquisition_id(self, experiment_id, plate_name, acquisition_name):
        '''Gets the ID of an :py:class:`tmlib.models.Acquisition` given its
        name, the name of its parent :py:class:`tmlib.models.Plate` and
        the ID of the parent :py:class:`tmlib.models.Experiment`.

        Parameters
        ----------
        experiment_id: str
            ID of the parent experiment
        plate_name: str
            name of the parent plate
        acquisition_name: str
            name of the acquisition

        Returns
        -------
        str
            acquisition ID
        '''
        logger.debug(
            'get acquisition ID given acquisition "%s", plate "%s" and '
            'experiment %s',
            acquisition_name, plate_name, experiment_id
        )
        data = {
            'plate_name': plate_name,
            'acquisition_name': acquisition_name
        }
        url = self.build_url(
            '/api/experiments/%s/acquisitions/id' % experiment_id
        )
        res = self.session.post(url, json=data)
        self._handle_error(res)
        return res.json()['id']

    def create_acquisition(self, experiment_id, plate_name, acquisition_name):
        '''Creates a new :py:class:`tmlib.models.Plate`.

        Parameters
        ----------
        experiment_id: str
            ID of the parent experiment
        plate_name: str
            name of the parent plate
        acquisition_id: str
            name that should be given to the acquisition
        '''
        logger.info(
            'create acquisition "%s" for plate "%s" of experiment %s',
            acquisition_name, plate_name, experiment_id
        )
        params = {
            'plate_name': plate_name,
            'acquisition_name': acquisition_name
        }
        url = self.build_url(
            '/api/experiments/%s/acquisitions' % experiment_id, params
        )
        res = self.session.post(url)
        self._handle_error(res)

    def get_cycle_id(self, experiment_id, plate_name, cycle_index):
        '''Gets the ID of a :py:class:`tmlib.models.Cycle` given its
        index, the name of the parent :py:class:`tmlib.models.Plate` and
        the ID of the parent :py:class:`tmlib.models.Experiment`.

        Parameters
        ----------
        experiment_id: str
            ID of the parent experiment
        plate_name: str
            name of the parent plate
        cycle_index: str
            index of the cycle

        Returns
        -------
        str
            cycle ID
        '''
        logger.debug(
            'get cycle ID given cycle #%d, plate "%s" and experiment %s',
            cycle_index, plate_name, experiment_id
        )
        params = {
            'plate_name': plate_name,
            'cycle_index': cycle_index
        }
        url = self.build_url(
            '/api/experiments/%s/cycles/id' % experiment_id, params
        )
        res = self.session.get(url)
        self._handle_error(res)
        return res.json()['id']

    def get_channel_id(self, experiment_id, channel_name):
        '''Gets the ID of a :py:class:`tmlib.models.Channel` given its
        name and the ID of the parent :py:class:`tmlib.models.Experiment`.

        Parameters
        ----------
        experiment_id: str
            ID of the parent experiment
        channel_name: str
            name of the channel

        Returns
        -------
        str
            channel ID
        '''
        logger.debug(
            'get channel ID given channel "%s" and experiment "%s"',
            channel_name, experiment_name
        )
        params = {
            'channel_name': channel_name,
        }
        url = self.build_url(
            '/api/experiments/%s/channels/id' % experiment_id, params
        )
        res = self.session.get(url)
        self._handle_error(res)
        return res.json()['id']

    def get_channel_layer_id(self, experiment_id, channel_name, tpoint=0, zplane=0):
        '''Gets the ID of a :py:class:`tmlib.models.Channel` given its
        name and the ID of the parent :py:class:`tmlib.models.Experiment`.

        Parameters
        ----------
        experiment_id: str
            ID of the parent experiment
        channel_name: str
            name of the channel
        tpoint: int, optional
            zero-based time point index (default: ``0``)
        zplane: int, optional
            zero-based z-plane index (default: ``0``)

        Returns
        -------
        str
            channel ID
        '''
        logger.debug(
            'get channel ID given channel "%s" and experiment "%s"',
            channel_name, experiment_name
        )
        params = {
            'channel_name': channel_name,
            'tpoint': tpoint,
            'zplane': zplane
        }
        url = self.build_url(
            '/api/experiments/%s/channel_layers/id' % experiment_id, params
        )
        res = self.session.get(url)
        self._handle_error(res)
        return res.json()['id']


