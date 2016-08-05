import requests
import json
import logging

from tmlib.utils import same_docstring_as

from tmclient.base import HttpClient

logger = logging.getLogger(__name__)


class ExperimentQueryService(HttpClient):

    '''Class for querying an experiment remotely stored in TissueMAPS via
    its RESTful API.

    Experiments and other objects belonging to an experiment (e.g. images)
    ofter need to be queried by their ID.
    '''

    @same_docstring_as(HttpClient.__init__)
    def __init__(self, hostname):
        super(ExperimentQueryService, self).__init__(hostname)

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

    def get_plate_id(self, experiment_name, plate_name):
        '''Gets the ID of a :py:class:`tmlib.models.Plate` given its name and
        the name of the parent :py:class:`tmlib.models.Experiment`.

        Parameters
        ----------
        experiment_name: str
            name of the parent experiment
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
            'experiment_name': experiment_name,
            'plate_name': plate_name,
        }
        url = self.build_url('/api/plates/id', params)
        res = self.session.get(url)
        self._handle_error(res)
        return res.json()['id']

    def get_acquisition_id(self, experiment_name, plate_name, acquisition_name):
        '''Gets the ID of an :py:class:`tmlib.models.Acquisition` given its
        name and the name of the parent :py:class:`tmlib.models.Experiment` and
        :py:class:`tmlib.models.Plate`.

        Parameters
        ----------
        experiment_name: str
            name of the parent experiment
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
            'experiment "%s"',
            acquisition_name, plate_name, experiment_name
        )
        params = {
            'experiment_name': experiment_name,
            'plate_name': plate_name,
            'acquisition_name': acquisition_name
        }
        url = self.build_url('/api/acquisitions/id', params)
        res = self.session.get(url)
        self._handle_error(res)
        return res.json()['id']

    def get_cycle_id(self, experiment_name, plate_name, cycle_index):
        '''Gets the ID of a :py:class:`tmlib.models.Cycle` given its
        index and the name of the parent :py:class:`tmlib.models.Experiment`
        and :py:class:`tmlib.models.Plate`.

        Parameters
        ----------
        experiment_name: str
            name of the parent experiment
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
            'get cycle ID given cycle #%d, plate "%s" and experiment "%s"',
            cycle_index, plate_name, experiment_name
        )
        params = {
            'experiment_name': experiment_name,
            'plate_name': plate_name,
            'cycle_index': cycle_index
        }
        url = self.build_url('/api/cycles/id', params)
        res = self.session.get(url)
        self._handle_error(res)
        return res.json()['id']

    def get_channel_id(self, experiment_name, channel_name):
        '''Gets the ID of a :py:class:`tmlib.models.Channel` given its
        name and the name of the parent :py:class:`tmlib.models.Experiment`.

        Parameters
        ----------
        experiment_name: str
            name of the parent experiment
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
            'experiment_name': experiment_name,
            'channel_name': channel_name,
        }
        url = self.build_url('/api/channels/id', params)
        res = self.session.get(url)
        self._handle_error(res)
        return res.json()['id']

