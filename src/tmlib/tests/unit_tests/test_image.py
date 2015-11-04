import os
import numpy as np
import unittest
from tmlib.image import ChannelImage
from tmlib.metadata import ChannelImageMetadata
from tmlib.pixels import VipsPixels
from cached_property import cached_property
from gi.repository import Vips
from tmlib.pixels import NumpyPixels
from scipy import misc


class TestImage(unittest.TestCase):

    def setUp(self):
        self.metadata = ChannelImageMetadata()
        testdata_dir = os.path.join(
                            os.path.dirname(__file__), '..', 'testdata')
        self.filename = os.path.join(
                            testdata_dir,
                            'test_t000_D03_y000_x000_c000_z000.png')
        self.np_array = misc.imread(self.filename).astype(np.uint16)
        self.vips_img = Vips.Image.new_from_file(self.filename)

    def tearDown(self):
        pass

    def test_create_image_from_file_vips_1(self):
        image = ChannelImage.create_from_file(self.filename, self.metadata)
        self.assertIsInstance(image.pixels, VipsPixels)

    def test_create_image_from_file_vips_2(self):
        image = ChannelImage.create_from_file(
                    self.filename, self.metadata, library='vips')
        self.assertIsInstance(image.pixels, VipsPixels)

    def test_create_image_from_file_numpy(self):
        image = ChannelImage.create_from_file(
                    self.filename, self.metadata, library='numpy')
        self.assertIsInstance(image.pixels, NumpyPixels)

    def test_align(self):
        pass

    def test_correct_illumination(self):
        pass


class TestVipsPixels(TestImage):

    @cached_property
    def pixels(self):
        return VipsPixels(self.vips_img)

    def test_create_from_file(self):
        pixels = VipsPixels.create_from_file(self.filename)
        self.assertIsInstance(pixels, VipsPixels)
        self.assertIsInstance(pixels.array, Vips.Image)
        self.assertEqual(pixels.array,
                         Vips.Image.new_from_file(self.filename))
        self.assertEqual(pixels.dtype, Vips.BandFormat.USHORT)
        self.assertEqual(pixels.dimensions,
                         (self.vips_img.height, self.vips_img.width))

    def test_create_from_np_array(self):
        pixels = VipsPixels.create_from_numpy_array(self.np_array)
        self.assertIsInstance(pixels, VipsPixels)
        self.assertIsInstance(pixels.array, Vips.Image)
        self.assertEqual(pixels.dtype, Vips.BandFormat.USHORT)
        self.assertEqual(pixels.dimensions, self.np_array.shape)
        self.assertEqual(pixels.dimensions,
                         (self.vips_img.height, self.vips_img.width))

    def test_initialize_with_wrong_datatype(self):
        with self.assertRaises(TypeError):
            VipsPixels(self.np_array)

    def test_dimensions_attribute(self):
        self.assertEqual(self.pixels.dimensions,
                         (self.vips_img.height, self.vips_img.width))

    def test_bands_attribute(self):
        self.assertEqual(self.pixels.bands, 1)

    def test_type_attributes(self):
        self.assertEqual(self.pixels.type, Vips.Image)
        self.assertEqual(self.pixels.dtype, Vips.BandFormat.USHORT)
        self.assertTrue(self.pixels.is_uint)
        self.assertFalse(self.pixels.is_float)
        self.assertFalse(self.pixels.is_binary)


class TestNumpyPixels(TestImage):

    @cached_property
    def pixels(self):
        return NumpyPixels(self.np_array)

    def test_create_from_file(self):
        pixels = NumpyPixels.create_from_file(self.filename)
        self.assertIsInstance(pixels, NumpyPixels)
        self.assertIsInstance(pixels.array, np.ndarray)
        self.assertEqual(pixels.dtype, self.np_array.dtype)
        self.assertEqual(pixels.dimensions, self.np_array.shape)

    def test_create_from_vips_image(self):
        pixels = NumpyPixels.create_from_vips_image(self.vips_img)
        self.assertIsInstance(pixels, NumpyPixels)
        self.assertIsInstance(pixels.array, np.ndarray)
        self.assertEqual(pixels.dtype, self.np_array.dtype)
        self.assertEqual(pixels.dimensions, self.np_array.shape)
        self.assertEqual(pixels.dimensions,
                         (self.vips_img.height, self.vips_img.width))

    def test_initialize_with_wrong_datatype(self):
        with self.assertRaises(TypeError):
            NumpyPixels(self.vips_img)

    def test_dimensions_attribute(self):
        self.assertEqual(self.pixels.dimensions,
                         self.np_array.shape)

    def test_bands_attribute(self):
        self.assertEqual(self.pixels.bands, 1)

    def test_type_attributes(self):
        self.assertEqual(self.pixels.type, np.ndarray)
        self.assertEqual(self.pixels.dtype, np.uint16)
        self.assertTrue(self.pixels.is_uint)
        self.assertFalse(self.pixels.is_float)
        self.assertFalse(self.pixels.is_binary)
