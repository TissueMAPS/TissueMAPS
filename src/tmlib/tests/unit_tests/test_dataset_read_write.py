import os
import logging
import random
import tempfile
import numpy as np
import unittest
from tmlib.readers import DatasetReader
from tmlib.writers import DatasetWriter

logger = logging.getLogger(__name__)


class TestDatasetReaderWriter(unittest.TestCase):

    def setUp(self):
        tmp_dir = tempfile.gettempdir()
        self.filename = os.path.join(tmp_dir, 'testfile.h5')

    def write_array_to_HDF5_file_and_read_it_back(self, arr_write):
        with DatasetWriter(self.filename, truncate=True) as writer:
            writer.write('arr', arr_write)
        with DatasetReader(self.filename) as reader:
            arr_read = reader.read('arr')
        return arr_read

    def assertEqualNumpy(self, actual, desired):
        np.testing.assert_array_equal(actual, desired)

    def assertEqualNumpyElementWise(self, actual, desired):
        [np.testing.assert_array_equal(actual[i], desired[i])
         for i in xrange(len(actual))]

    def test_atomic_dataset(self):
        logger.info('test ATOMIC dataset')
        arr_write = np.array(np.random.random((1000, 1500)))
        arr_read = self.write_array_to_HDF5_file_and_read_it_back(arr_write)
        self.assertEqualNumpy(arr_write, arr_read)

    def test_compound_dataset(self):
        logger.info('test COMPOUND dataset')
        arr_write = list()
        for i in xrange(100):
            arr_write.append(np.empty((random.randint(100, 10000))))
        arr_write = np.array(arr_write)
        arr_read = self.write_array_to_HDF5_file_and_read_it_back(arr_write)
        # np.testing.assert_array_equal() fails on arrays of type "O"
        self.assertEqualNumpyElementWise(arr_write, arr_read)
