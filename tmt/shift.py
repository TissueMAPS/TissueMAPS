import os
import numpy as np
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


def shift_and_crop_image(im, y, x, upper, lower, left, right):
    '''
    Shift and crop an image according to the calculated values shift and
    overlap values.

    Parameters
    ----------
    im: numpy.ndarray
        input image
    y: int
        shift in y direction (positive value -> down, negative value -> up)
    x: int
        shift in x direction (position value -> right, negative value -> left)
    upper: int
        upper overlap - pixels cropped from the bottom
    lower: int
        lower overlap - pixels cropped form the top
    left: int
        left overlap - pixels cropped form the right
    right: int
        right overlap - pixels cropped from the left

    Returns
    -------
    numpy.array
        shifted and cropped image

    Raises
    ------
    IndexError
        when shift or overlap values are too extreme
    Exception
        when it fails for unknown reasons
    '''
    # TODO: check that Vips works correctly
    try:
        if isinstance(im, np.ndarray):
            # we may loose one pixel when shift values are zero
            return im[(lower-y):-(upper+y+1), (right-x):-(left+x+1)]
        else:
            return im.crop(right-x, lower-y,
                           im.width-left-right, im.height-upper-lower)
    except IndexError as e:
        raise IndexError('Shifting and cropping of the image failed!\n'
                         'Shift or overlap values are incorrect:\n%s' % str(e))
    except Exception as e:
        raise Exception('Shifting and cropping of the image failed!\n'
                        'Reason: %s' % str(e))


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
    def required_keys(self):
        self._required_keys = {
            'xShift', 'yShift', 'fileName',
            'lowerOverlap', 'upperOverlap', 'rightOverlap', 'leftOverlap',
            'maxShift', 'noShiftIndex', 'noShiftCount',
            'segmentationDir', 'segmentationFilenameTrunk', 'cycleNum'
        }
        return self._required_keys

    def _check_descriptor(self, content):
        if not content:
            raise IOError('Shift descriptor is empty: "%s"' % self.filename)
        for key in content:
            if key not in self.required_keys:
                raise KeyError('Shift descriptor must have key "%s"' % key)

    @property
    def description(self):
        '''
        Returns
        -------
        Namespacified
            content of a JSON shift descriptor file
            with the following name spaces:

            |    xShift
            |    yShift
            |    fileName
            |    lowerOverlap
            |    upperOverlap
            |    rightOverlap
            |    leftOverlap
            |    maxShift
            |    noShiftIndex
            |    noShiftCount
            |    segmentationDir
            |    segmentationFilenameTrunk
            |    cycleNum

        Raises
        ------
        IOError
            when file is empty
        '''
        if self._description is None:
            content = load_shift_descriptor(self.filename)
            self._check_descriptor(content)
            self._description = tmt.util.Namespacified(content)
        return self._description

    def align(self, im, im_name):
        '''
        Align, i.e. shift and crop, an image based on calculated shift
        and overlap values.

        Parameters
        ----------
        im: numpy.ndarray or Vips.Image
            input image that should be aligned
        im_name: str
            name of the image file

        Returns
        -------
        numpy.ndarray or Vips.Image
            aligned image
        '''
        index = [i for i, f in enumerate(self.description.fileName)
                 if f == im_name][0]
        y = self.description.yShift[index]
        x = self.description.xShift[index]
        upper = self.description.upperOverlap
        lower = self.description.lowerOverlap
        left = self.description.leftOverlap
        right = self.description.rightOverlap
        return shift_and_crop_image(im, y, x, upper, lower, left, right)
