import numpy as np
import collections
import jtapi


def initial_py_module(**kwargs):
    InputImage = np.random.random((100, 100, 10))

    print('>>>>> Image has type "{0}" and dimensions "{1}".'.format(
          str(InputImage.dtype), str(InputImage.shape)))

    print('>>>>> Pixel value at position [1, 2] (0-based): {0}'.format(
          InputImage[1, 2]))

    data = dict()
    jtapi.writedata(data, kwargs['data_file'])

    output = collections.namedtuple('Output', ['OutputImage'])
    return output(InputImage)
