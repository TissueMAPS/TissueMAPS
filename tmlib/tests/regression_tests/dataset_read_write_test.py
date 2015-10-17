#!/usr/bin/env python
import logging
import tempfile
import random
import numpy as np
from tmlib.readers import DatasetReader
from tmlib.writers import DatasetWriter
from tmlib.logging_utils import configure_logging
from tmlib.logging_utils import map_logging_verbosity
from tmlib.testing.argparser import parser
from tmlib.testing import logo

logger = logging.getLogger(__name__)


class TestDatasetReaderWriter(object):

    def write_array_to_HDF5_file_and_read_to_back(self, arr_write):
        logger.debug('content of written array:\n{arr}'.format(arr=arr_write))

        filename = '{dir}_{name}'.format(dir=tempfile.gettempdir(),
                                         name=self.__class__.__name__)
        logger.info('write array to HDF5 file: {0}'.format(filename))

        with DatasetWriter(filename, truncate=True) as writer:
            writer.write('arr', arr_write)

        logger.info('read array back from HDF5 file: {0}'.format(filename))
        with DatasetReader(filename) as reader:
            arr_read = reader.read('arr')

        logger.debug('content of read array:\n{arr}'.format(arr=arr_read))
        return arr_read

    def assertEqualNumpy(self, actual, desired):
        logger.info('assert equality of elements between arrays')

        logger.info('dimension of written array: {0}'.format(actual.shape))
        logger.info('dimension of read array: {0}'.format(desired.shape))

        logger.info('data type of written array: {0}'.format(actual.dtype))
        logger.info('data type of read array: {0}'.format(desired.dtype))

        logger.info('data type of elements of written array: {0}'.format(
                        set(np.unique([e.dtype for e in actual]))))
        logger.info('data type of elements of read array: {0}'.format(
                        set(np.unique([e.dtype for e in desired]))))

        np.testing.assert_array_equal(actual, desired)
        logger.info('arrays are equal')

        [np.testing.assert_array_equal(actual[i], desired[i])
         for i in xrange(len(actual))]
        logger.info('arrays are equal when compared element wise')

    def test_atomic_dataset(self):
        logger.info('test ATOMIC dataset')
        arr_write = np.array(np.random.random((1000, 1500)))
        arr_read = self.write_array_to_HDF5_file_and_read_to_back(arr_write)
        self.assertEqualNumpy(arr_write, arr_read)

    def test_compound_dataset(self):
        logger.info('test COMPOUND dataset')
        arr_write = list()
        for i in xrange(100):
            arr_write.append(np.empty((random.randint(100, 10000))))
        arr_write = np.array(arr_write)
        arr_read = self.write_array_to_HDF5_file_and_read_to_back(arr_write)
        self.assertEqualNumpy(arr_write, arr_read)


if __name__ == '__main__':

    args = parser.parse_args()

    print logo

    level = map_logging_verbosity(args.verbosity)
    configure_logging(level)

    TestDatasetReaderWriter().test_atomic_dataset()
    TestDatasetReaderWriter().test_compound_dataset()
