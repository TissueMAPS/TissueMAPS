class NotSupportedError(Exception):
    '''
    Error class that should be raised when a feature is not supported by the
    program.
    '''
    pass


class MetadataError(Exception):
    '''
    Error class that should be raised when a metadata element cannot be
    retrieved. 
    '''
    pass
