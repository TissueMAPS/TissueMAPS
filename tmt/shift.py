import os
import json
import tmt


def load_shift_descriptor(filename):
    '''
    Load shift description from JSON file.

    Parameters
    ----------
    filename: str
        name of the shift descriptor file

    Returns
    -------
    dict
        JSON content
    '''
    if not os.path.exists(filename):
        raise OSError('Shift descriptor file does not exist: %s' % filename)
    with open(filename) as f:
        return json.load(f)


class ShiftDescriptor(object):
    '''
    Utility class for a shift descriptor.

    A shift descriptor is file in JSON format, which holds calculated shift
    values and additional metainformation.

    See also
    --------
    `tmt.corilla` package
    '''

    def __init__(self, filename, cfg):
        '''
        Initialize ShiftDescriptor class.

        Parameters
        ----------
        filename: str
            path to the JSON shift descriptor file
        cfg: Dict[str, str]
            configuration settings
        '''
        self.filename = filename
        self.cfg = cfg
        self._description = None

    @property
    def description(self):
        '''
        Returns
        -------
        Namespacified
            content of a JSON shift descriptor file

        Raises
        ------
        IOError
            when file is empty
        '''
        if self._description is None:
            content = load_shift_descriptor(self.filename)
            if not content:
                raise IOError('Shift descriptor file "%s" doesn\'t contain '
                              'any description' % self.filename)
            self._description = tmt.util.Namespacified(content)
        return self._description
