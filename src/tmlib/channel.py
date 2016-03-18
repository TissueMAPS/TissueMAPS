import re
import os
import logging
from natsort import natsorted
from cached_property import cached_property
from . import utils
from .layer import ChannelLayer
from .layer import LayerIndex
from .errors import RegexError

logger = logging.getLogger(__name__)


class Channel(object):

    '''
    Class for a channel which holds a set of layers.
    '''

    CHANNEL_DIR_FORMAT = 'channel_{index:0>3}'

    def __init__(self, channel_dir, image_files):
        '''
        Parameters
        ----------
        channel_dir: str
            absolute path to the channel directory
        image_files: List[str]
            absolute path to image files which belong to this channel
        '''
        self.channel_dir = channel_dir
        self._name = None

    @property
    def dir(self):
        '''
        Returns
        -------
        str
            absolute path to the channel directory
        '''
        return self.channel_dir

    @property
    def name(self):
        '''
        Returns
        -------
        str
            name of the channel
        '''
        if self._name is None:
            self._name = cfg.CHANNEL_NAME_FORMAT.format(c=self.index)
        return self._name

    @name.setter
    def name(self, value):
        if not isinstance(value, basestring):
            raise TypeError('Attribute "name" must have type basestring.')
        self._name = value
    

    @property
    def index(self):
        '''
        Each `channel` has a zero-based identifier number.
        It is encoded in the name of the folder and is retrieved from
        it using a regular expression.

        Returns
        -------
        int
            zero-based channel identifier number

        Raises
        ------
        tmlib.errors.RegexError
            when `index` cannot not be determined from folder name

        See also
        --------
        :py:attribute:`tmlib.channel.Channel.CHANNEL_DIR_FORMAT`
        '''
        folder_name = os.path.basename(self.dir)
        regexp = utils.regex_from_format_string(self.CHANNEL_DIR_FORMAT)
        match = re.search(regexp, folder_name)
        if not match:
            raise RegexError(
                    'Can\'t determine channel index from folder "%s".'
                    % folder_name)
        return int(match.group('index'))

    def _is_layer_dir(self, folder):
        format_string = ChannelLayer.LAYER_DIR_FORMAT
        regexp = utils.regex_from_format_string(format_string)
        return True if re.match(regexp, folder) else False

    @cached_property
    def layers(self):
        '''
        Returns
        -------
        Dict[tmlib.layer.LayerIndex[int], tmlib.layer.ChannelLayer]
            layer objects for each `tpoint` `zplane` combination

        Raises
        ------
        tmlib.errors.RegexError
            when `tpoint` and `zplane` cannot not be determined from
            folder name
        '''
        layer_dirs = [
            os.path.join(self.dir, d)
            for d in os.listdir(self.dir)
            if os.path.isdir(os.path.join(self.dir, d)) and
            self._is_layer_dir(d) and
            not d.startswith('.')
        ]
        layer_dirs = natsorted(layer_dirs)
        regexp = utils.regex_from_format_string(ChannelLayer.LAYER_DIR_FORMAT)
        match = re.search(regexp, folder_name)
        if not match:
            raise RegexError(
                    'Can\'t determine time point and z-plane index from '
                    'folder "%s".' % folder_name)
        indices = match.groupdict()
        index = LayerIndex(int(indices['t']), int(indices['z']))
        return {
            index: ChannelLayer(layer_dir=d) for d in layer_dirs
        }

    def add_layer(self, tpoint, zplane):
        '''
        Add a layer to the channel, i.e. create a folder on disk and append the
        list of existing layer objects.

        Returns
        -------
        tmlib.cycle.ChannelLayer
            layer object
        '''
        new_layer_name = ChannelLayer.LAYER_DIR_FORMAT.format(t=tpoint, z=zplane)
        new_layer_dir = os.path.join(self.dir, new_layer_name)
        if os.path.exists(new_layer_dir):
            raise OSError('ChannelLayer "%s" already exists.')
        logger.debug('add layer: t %d and z %d', tpoint, zplane)
        logger.debug('create directory for new layer: %s', new_layer_dir)
        os.mkdir(new_layer_dir)
        new_layer = ChannelLayer(cycle_dir=new_layer_dir)
        index = LayerIndex(tpoint, zplane)
        self.layers.update({index: new_layer})
        return new_layer
