import os
import numpy as np
import unittest
from cached_property import cached_property
from gi.repository import Vips
from scipy import misc
from tmlib.pixels import NumpyPixels
from tmlib.image import ChannelImage
from tmlib.image import IllumstatsImages
from tmlib.metadata import ChannelImageMetadata
from tmlib.metadata import IllumstatsImageMetadata
from tmlib.pixels import VipsPixels


class TestImageSetup(unittest.TestCase):

    def setUp(self):
        # TODO: mock attributes instead of using large files
        self.metadata = ChannelImageMetadata()
        testdata_dir = os.path.join(
                                os.path.dirname(__file__), '..', 'testdata')
        self.img_filename = os.path.join(
                                testdata_dir,
                                'test_t000_D03_y000_x000_c000_z000.png')
        self.stats_filename = os.path.join(
                                testdata_dir,
                                'channel_0.stat.h5')
        self.np_array = misc.imread(self.img_filename).astype(np.uint16)
        self.vips_img = Vips.Image.new_from_file(self.img_filename)

    def tearDown(self):
        pass


class TestImage(TestImageSetup):

    def test_create_image_from_file_vips_1(self):
            image = ChannelImage.create_from_file(self.img_filename,
                                                  self.metadata)
            self.assertIsInstance(image.pixels, VipsPixels)

    def test_create_image_from_file_vips_2(self):
        image = ChannelImage.create_from_file(
                    self.img_filename, self.metadata, library='vips')
        self.assertIsInstance(image.pixels, VipsPixels)

    def test_create_image_from_file_numpy(self):
        image = ChannelImage.create_from_file(
                    self.img_filename, self.metadata, library='numpy')
        self.assertIsInstance(image.pixels, NumpyPixels)

    def test_align_vips_crop_1(self):
        image = ChannelImage.create_from_file(self.img_filename, self.metadata)
        image.metadata.x_shift = 1
        image.metadata.y_shift = 2
        image.metadata.upper_overhang = 5
        image.metadata.lower_overhang = 6
        image.metadata.right_overhang = 7
        image.metadata.left_overhang = 8
        aligned_image = image.align(crop=True)
        self.assertIsInstance(aligned_image, ChannelImage)
        diff_0 = image.metadata.upper_overhang + image.metadata.lower_overhang
        self.assertEqual(aligned_image.pixels.dimensions[0],
                         image.pixels.dimensions[0]-diff_0)
        diff_1 = image.metadata.right_overhang + image.metadata.left_overhang
        self.assertEqual(aligned_image.pixels.dimensions[1],
                         image.pixels.dimensions[1]-diff_1)

    def test_align_vips_crop_2(self):
        image = ChannelImage.create_from_file(self.img_filename, self.metadata)
        aligned_image = image.align(crop=True)
        self.assertIsInstance(aligned_image, ChannelImage)
        diff_0 = image.metadata.upper_overhang + image.metadata.lower_overhang
        self.assertEqual(aligned_image.pixels.dimensions[0],
                         image.pixels.dimensions[0]-diff_0)
        diff_1 = image.metadata.right_overhang + image.metadata.left_overhang
        self.assertEqual(aligned_image.pixels.dimensions[1],
                         image.pixels.dimensions[1]-diff_1)

    def test_align_vips_not_crop_1(self):
        image = ChannelImage.create_from_file(self.img_filename, self.metadata)
        image.x_shift = 1
        image.y_shift = 2
        image.upper_overhang = 5
        image.lower_overhang = 6
        image.right_overhang = 7
        image.left_overhang = 8
        aligned_image = image.align(crop=False)
        self.assertIsInstance(aligned_image, ChannelImage)
        self.assertEqual(aligned_image.pixels.dimensions,
                         image.pixels.dimensions)

    def test_align_vips_not_crop_2(self):
        image = ChannelImage.create_from_file(self.img_filename, self.metadata)
        aligned_image = image.align(crop=False)
        self.assertIsInstance(aligned_image, ChannelImage)
        self.assertEqual(aligned_image.pixels.dimensions,
                         image.pixels.dimensions)

    def test_correct_illumination_vips(self):
        metadata = IllumstatsImageMetadata()
        metadata.tpoint_ix = 0
        metadata.channel_ix = 0
        self.metadata.tpoint_ix = 0
        self.metadata.channel_ix = 0
        stats = IllumstatsImages.create_from_file(self.stats_filename, metadata)
        image = ChannelImage.create_from_file(self.img_filename, self.metadata)
        corrected_image = image.correct(stats)
        self.assertIsInstance(corrected_image, ChannelImage)

    def test_align_np_crop_1(self):
        image = ChannelImage.create_from_file(self.img_filename, self.metadata,
                                              library='numpy')
        image.metadata.x_shift = 1
        image.metadata.y_shift = 2
        image.metadata.upper_overhang = 5
        image.metadata.lower_overhang = 6
        image.metadata.right_overhang = 7
        image.metadata.left_overhang = 8
        aligned_image = image.align(crop=True)
        self.assertIsInstance(aligned_image, ChannelImage)
        diff_0 = image.metadata.upper_overhang + image.metadata.lower_overhang
        self.assertEqual(aligned_image.pixels.dimensions[0],
                         image.pixels.dimensions[0]-diff_0)
        diff_1 = image.metadata.right_overhang + image.metadata.left_overhang
        self.assertEqual(aligned_image.pixels.dimensions[1],
                         image.pixels.dimensions[1]-diff_1)

    def test_align_np_crop_2(self):
        image = ChannelImage.create_from_file(self.img_filename, self.metadata,
                                              library='numpy')
        aligned_image = image.align(crop=True)
        self.assertIsInstance(aligned_image, ChannelImage)
        diff_0 = image.metadata.upper_overhang + image.metadata.lower_overhang
        self.assertEqual(aligned_image.pixels.dimensions[0],
                         image.pixels.dimensions[0]-diff_0)
        diff_1 = image.metadata.right_overhang + image.metadata.left_overhang
        self.assertEqual(aligned_image.pixels.dimensions[1],
                         image.pixels.dimensions[1]-diff_1)

    def test_align_np_not_crop_1(self):
        image = ChannelImage.create_from_file(self.img_filename, self.metadata,
                                              library='numpy')
        image.x_shift = 1
        image.y_shift = 2
        image.upper_overhang = 5
        image.lower_overhang = 6
        image.right_overhang = 7
        image.left_overhang = 8
        aligned_image = image.align(crop=False)
        self.assertIsInstance(aligned_image, ChannelImage)
        self.assertEqual(aligned_image.pixels.dimensions,
                         image.pixels.dimensions)

    def test_align_np_not_crop_2(self):
        image = ChannelImage.create_from_file(self.img_filename, self.metadata,
                                              library='numpy')
        aligned_image = image.align(crop=False)
        self.assertIsInstance(aligned_image, ChannelImage)
        self.assertEqual(aligned_image.pixels.dimensions,
                         image.pixels.dimensions)

    def test_correct_illumination_np(self):
        metadata = IllumstatsImageMetadata()
        metadata.tpoint_ix = 0
        metadata.channel_ix = 0
        self.metadata.tpoint_ix = 0
        self.metadata.channel_ix = 0
        stats = IllumstatsImages.create_from_file(self.stats_filename,
                                                  metadata, library='numpy')
        image = ChannelImage.create_from_file(self.img_filename, self.metadata,
                                              library='numpy')
        corrected_image = image.correct(stats)
        self.assertIsInstance(corrected_image, ChannelImage)


class TestVipsPixels(TestImageSetup):

    @cached_property
    def pixels(self):
        return VipsPixels(self.vips_img)

    def test_create_from_file(self):
        pixels = VipsPixels.create_from_file(self.img_filename)
        self.assertIsInstance(pixels, VipsPixels)
        self.assertIsInstance(pixels.array, Vips.Image)
        self.assertEqual(pixels.array,
                         Vips.Image.new_from_file(self.img_filename))
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


class TestNumpyPixels(TestImageSetup):

    @cached_property
    def pixels(self):
        return NumpyPixels(self.np_array)

    def test_create_from_file(self):
        pixels = NumpyPixels.create_from_file(self.img_filename)
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
