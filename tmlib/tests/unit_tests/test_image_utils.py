#!/usr/bin/env python
import unittest
import numpy as np
from gi.repository import Vips
from tmlib import image_utils


class TestImageUtils(unittest.TestCase):

    def setUp(self):
        pass

    def test_convert_vips_image_to_numpy_array(self):
        numpy_array = np.random.random((10, 10))
        vips_image = Vips.Image.new_from_array(numpy_array.tolist())
        conv_numpy_array = image_utils.vips_image_to_np_array(vips_image)
        np.testing.assert_array_equal(numpy_array, conv_numpy_array)

    def test_convert_numpy_array_to_vips_image(self):
        numpy_array = np.random.random((10, 10))
        vips_image = Vips.Image.new_from_array(numpy_array.tolist())
        conv_vips_image = image_utils.np_array_to_vips_image(numpy_array)
        self.assertEqual(vips_image, conv_vips_image)

if __name__ == '__main__':

    unittest.main()
