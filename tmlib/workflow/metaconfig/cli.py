import logging

from tmlib.utils import assert_type
from tmlib.workflow.cli import CommandLineInterface

logger = logging.getLogger(__name__)


class Metaconfig(CommandLineInterface):

    @assert_type(api_instance='tmlib.workflow.metaconfig.api.MetadataConfigurator')
    def __init__(self, api_instance):
        '''
        Parameters
        ----------
        api_instance: tmlib.workflow.metaconfig.api.MetadataConfigurator
            instance of API class to which processing is delegated
        '''
        super(Metaconfig, self).__init__(api_instance)

