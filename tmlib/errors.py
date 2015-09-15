class NotSupportedError(Exception):
    '''
    Error class that is raised when a feature is not supported by the program.
    '''


class MetadataError(Exception):
    '''
    Error class that is raised when a metadata element cannot be retrieved.
    '''


class SubmissionError(Exception):
    '''
    Error class that is raised when submitted jobs failed.
    '''


class CliArgError(Exception):
    '''
    Error class that is raised when the value of an command line argument is
    invalid.
    '''


class RegexpError(Exception):
    '''
    Error class that is raised when a regular expression pattern didn't match.
    '''
