class FileUploadStatus(object):

    '''Upload status of a file.'''

    #: The file is registered, but upload not yet started
    WAITING = 'WAITING'

    #: Upload is ongoing
    UPLOADING = 'UPLOADING'

    #: Upload is complete
    COMPLETE = 'COMPLETE'

    #: Upload has failed
    FAILED = 'FAILED'

