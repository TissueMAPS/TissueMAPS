class SetupDescriptionError(Exception):
    '''Exception class for erronous setup description.'''


class SetupEnvironmentError(Exception):
    '''Exception class for missing environment variables required for setup.'''


class CloudError(Exception):
    '''Error class for interactions with cloud clients.'''


class NoInstanceFoundError(CloudError):
    '''Error class for situations where no matching instance is found.'''


class MultipleInstancesFoundError(CloudError):
    '''Error class for situations where multiple matching instances are found.'''

