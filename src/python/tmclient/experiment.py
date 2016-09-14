import requests
import json
import inspect
import logging

from tmclient.base import HttpClient

logger = logging.getLogger(__name__)


class ExperimentService(HttpClient):

    '''Class for querying a TissueMAPS experiment via RESTful API.'''

    def __init__(self, host_name, experiment_name, user_name, password=None):
        '''
        Parameters
        ----------
        host_name: str
            name of the TissueMAPS instance
        experiment_name: str
            name of the experiment that should be queried
        user_name: str
            name of the TissueMAPS user
        password: str
            password for `username`
        '''
        super(ExperimentService, self).__init__(host_name, user_name, password)
        self.experiment_name = experiment_name
        self._experiment_id = self._get_experiment_id(experiment_name)

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
        logger.debug('call method "%s"', method_name)
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

    def _get_experiment_id(self, experiment_name):
        '''Gets the ID of an existing experiment given its name.

        Parameters
        ----------
        experiment_name: str
            name of the experiment

        Returns
        -------
        str
            experiment ID

        See also
        --------
        :py:class:`tmlib.models.Experiment`
        :py:class:`tmlib.models.ExperimentReference`
        '''
        logger.debug('get ID for experiment "%s"', experiment_name)
        params = {
            'experiment_name': experiment_name,
        }
        url = self.build_url('/api/experiments/id', params)
        res = self.session.get(url)
        self._handle_error(res)
        return res.json()['id']

    def create_experiment(self, microscope_type, plate_format,
            plate_acquisition_mode):
        '''Creates a new experiment.

        Parameters
        ----------
        microscope_type: str
            microscope_type
        plate_format: int
            well-plate format, i.e. total number of wells per plate
        plate_acquisition_mode: str
            mode of image acquisition that determines whether acquisitions will
            be interpreted as time points as part of a time series experiment
            or as multiplexing cycles as part of a serial multiplexing
            experiment

        See also
        --------
        :py:class:`tmlib.models.Experiment`
        '''
        logger.info('create experiment "%s"', experiment_name)
        data = {
            'name': self.experiment_name,
            'microscope_type': microscope_type,
            'plate_format': plate_format,
            'plate_acquisition_mode': plate_acquisition_mode
        }
        url = self.build_url('/api/experiments')
        res = self.session.post(url, json=data)
        self._handle_error(res)

    def _get_plate_id(self, plate_name):
        '''Gets the ID of an existing plate given its name.

        Parameters
        ----------
        plate_name: str
            name of the plate

        Returns
        -------
        str
            plate ID

        See also
        --------
        :py:class:`tmlib.models.Plate`
        '''
        logger.debug('get ID for plate "%s"' % plate_name)
        params = {
            'plate_name': plate_name,
        }
        url = self.build_url(
            '/api/experiments/%s/plates/id' % self._experiment_id, params
        )
        res = self.session.get(url)
        self._handle_error(res)
        return res.json()['id']

    def create_plate(self, plate_name):
        '''Creates a new plate.

        Parameters
        ----------
        plate_name: str
            name that should be given to the plate

        See also
        --------
        :py:class:`tmlib.models.Plate`
        '''
        logger.info('create plate "%s"', plate_name)
        data = {
            'name': plate_name,
        }
        url = self.build_url('/api/experiments/%s/plates' % self._experiment_id)
        res = self.session.post(url, json=data)
        self._handle_error(res)

    def _get_acquisition_id(self, plate_name, acquisition_name):
        '''Gets the ID of an existing acquisition given its name and the name
        of the parent plate.

        Parameters
        ----------
        plate_name: str
            name of the parent plate
        acquisition_name: str
            name of the acquisition

        Returns
        -------
        str
            acquisition ID

        See also
        --------
        :py:class:`tmlib.models.Acquisition`
        '''
        logger.debug(
            'get acquisition ID given acquisition "%s" and plate "%s"',
            acquisition_name, plate_name
        )
        params = {
            'plate_name': plate_name,
            'acquisition_name': acquisition_name
        }
        url = self.build_url(
            '/api/experiments/%s/acquisitions/id' % self._experiment_id,
            params
        )
        res = self.session.get(url)
        self._handle_error(res)
        return res.json()['id']

    def create_acquisition(self, plate_name, acquisition_name):
        '''Creates a new acquisition.

        Parameters
        ----------
        plate_name: str
            name of the parent plate
        acquisition_name: str
            name that should be given to the acquisition

        See also
        --------
        :py:class:`tmlib.models.Acquisition`
        '''
        logger.info(
            'create acquisition "%s" for plate "%s"',
            acquisition_name, plate_name
        )
        data = {
            'plate_name': plate_name,
            'name': acquisition_name
        }
        url = self.build_url(
            '/api/experiments/%s/acquisitions' % self._experiment_id
        )
        res = self.session.post(url, json=data)
        self._handle_error(res)

    def _get_cycle_id(self, plate_name, cycle_index):
        '''Gets the ID of a cycle given its index, the name of the parent plate
        and ID of the parent experiment.

        Parameters
        ----------
        plate_name: str
            name of the parent plate
        cycle_index: str
            index of the cycle

        Returns
        -------
        str
            cycle ID

        See also
        --------
        :py:class:`tmlib.models.Cycle`
        '''
        logger.debug(
            'get cycle ID given cycle #%d and plate "%s"',
            cycle_index, plate_name
        )
        params = {
            'plate_name': plate_name,
            'cycle_index': cycle_index
        }
        url = self.build_url(
            '/api/experiments/%s/cycles/id' % self._experiment_id, params
        )
        res = self.session.get(url)
        self._handle_error(res)
        return res.json()['id']

    def _get_channel_id(self, channel_name):
        '''Gets the ID of a channel given its name.

        Parameters
        ----------
        channel_name: str
            name of the channel

        Returns
        -------
        str
            channel ID

        See also
        --------
        :py:class:`tmlib.models.Channel`
        '''
        logger.debug('get channel ID given channel "%s"', channel_name)
        params = {
            'channel_name': channel_name,
        }
        url = self.build_url(
            '/api/experiments/%s/channels/id' % self._experiment_id, params
        )
        res = self.session.get(url)
        self._handle_error(res)
        return res.json()['id']

    def _get_channel_layer_id(self, channel_name, tpoint=0, zplane=0):
        '''Gets the ID of a channel layer given the name of the parent channel
        as well as time point and z-plane indices.

        Parameters
        ----------
        channel_name: str
            name of the channel
        tpoint: int, optional
            zero-based time point index (default: ``0``)
        zplane: int, optional
            zero-based z-plane index (default: ``0``)

        Returns
        -------
        str
            channel layer ID

        See also
        --------
        :py:class:`tmlib.models.ChannelLayer`
        '''
        logger.debug(
            'get channel ID given channel "%s", tpoint %d and zplane %d',
            channel_name, tpoint, zplane
        )
        params = {
            'channel_name': channel_name,
            'tpoint': tpoint,
            'zplane': zplane
        }
        url = self.build_url(
            '/api/experiments/%s/channel_layers/id' % self._experiment_id,
            params
        )
        res = self.session.get(url)
        self._handle_error(res)
        return res.json()['id']


