import numpy as np
from scipy import misc
import collections
import jtapi


def initial_py_module(ImageFilename, **kwargs):
    print '>>>>> Loading image "%s"' % ImageFilename
    InputImage = np.array(misc.imread(ImageFilename), dtype='float64')

    print('>>>>> Image has type "%s" and dimensions "%s".' %
          (str(InputImage.dtype), str(InputImage.shape)))

    print('>>>>> Pixel value at position [1, 2] (0-based): %d' %
          InputImage[1, 2])

    data = dict()
    jtapi.writedata(data, kwargs['data_file'])

    output = collections.namedtuple('Output', ['OutputImage'])
    return output(InputImage)
