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


class JobDescriptionError(OSError):
    '''
    Error class that is raised when no job descriptor files are found.
    '''


class CliArgError(Exception):
    '''
    Error class that is raised when the value of an command line argument is
    invalid.
    '''


class RegexError(Exception):
    '''
    Error class that is raised when a regular expression pattern didn't match.
    '''


class StitchError(Exception):
    '''
    Error class that is raised when an error occurs upon stitching of
    images for the generation of a mosaic.
    '''


class PipelineError(Exception):
    '''
    Base class for jterator pipeline errors.
    '''


class PipelineRunError(PipelineError):
    '''
    Error class that is raised when an error occurs upon running a jterator
    pipeline.
    '''


class PipelineDescriptionError(PipelineError):
    '''
    Error class that is raised when information in pipeline description is
    missing or incorrect.
    '''


class PipelineOSError(PipelineError):
    '''
    Error class that is raised when pipeline related files do not exist
    on disk.
    '''


class WorkflowError(Exception):
    '''
    Base class for workflow errors.
    '''

class WorkflowDescriptionError(WorkflowError):
    '''
    Error class that is raised when the workflow is not correctly described.
    '''


class WorkflowNextStepError(WorkflowError):
    '''
    Error class that is raised when requirements for progressing to the next
    step are not fulfilled.
    '''
