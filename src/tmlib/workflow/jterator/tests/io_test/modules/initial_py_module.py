import numpy as np
import collections
import jtlib


def initial_py_module(**kwargs):
    InputImage = np.arange(300).reshape((3, 10, 10)).astype(np.uint16)

    output = collections.namedtuple('Output', ['OutputImage'])
    return output(InputImage)
