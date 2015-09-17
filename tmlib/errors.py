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


class StitchError(Exception):
    '''
    Error class that is raised when an error occurs upon stitching of
    images for the generation of a mosaic.
    '''


class PipelineRunError(Exception):
    '''
    Error class that is raised when an error occurs upon running a jterator
    pipeline.
    '''


class PipelineDescriptionError(Exception):
    '''
    Error class that is raised when information in pipeline description is
    missing or incorrect.
    '''


class PipelineOSError(Exception):
    '''
    Error class that is raised when pipeline related files do not exist
    on disk.
    '''
