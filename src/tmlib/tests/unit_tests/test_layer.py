import os
import unittest
import logging
from cached_property import cached_property
from gi.repository import Vips
from tmlib.experiment import Experiment
from tmlib.layer import ChannelLayer
from tmlib.mosaic import Mosaic
from tmlib.metadata import MosaicMetadata


class TestLayer(unittest.TestCase):

    def setUp(self):
        testdata_dir = os.path.join(os.path.dirname(__file__), '..', 'testdata')
        experiment_dir = os.path.join(testdata_dir, 'testExperiment')
        self.experiment = Experiment(experiment_dir)

    def tearDown(self):
        pass

    def test_create_layer_from_files(self):
        spacer_size = 10
        layer = ChannelLayer.create(
                    experiment=self.experiment,
                    tpoint_ix=0, channel_ix=0, zplane_ix=0,
                    spacer_size=spacer_size)
        self.assertIsInstance(layer, ChannelLayer)
        self.assertIsInstance(layer.mosaic, Mosaic)
        self.assertIsInstance(layer.mosaic.array, Vips.Image)
        self.assertIsInstance(layer.metadata, MosaicMetadata)
        self.assertEqual(layer.mosaic.dtype, Vips.BandFormat.USHORT)
        # There are two plates with one well each, so there should be
        #  vertically:
        #   - one spacer at the beginning of the first plate
        #   - two spacer between plates
        #   - one spacer at the end of the second plate
        #  horizontally:
        #   - one spacer at the beginning of each row
        #   - one spacer at the end of each row
        vert_gaps = 4 * spacer_size
        horz_gaps = 2 * spacer_size
        img_dims = (10, 10)
        exp_height = (vert_gaps + 2 * img_dims[0] * 2)
        exp_width = (horz_gaps + 2 * img_dims[1])
        self.assertEqual(layer.mosaic.dimensions, (exp_height, exp_width))

    @cached_property
    def layer(self):
        return ChannelLayer.create(
                    experiment=self.experiment,
                    tpoint_ix=0, channel_ix=0, zplane_ix=0)

    def test_clip_value(self):
        value = 100
        clipped_layer = self.layer.clip(value=value)
        self.assertEqual(clipped_layer.mosaic.array.max(), value)

    def test_clip_percentile(self):
        percentile = 99
        clipped_layer = self.layer.clip(percentile=percentile)
        self.assertEqual(clipped_layer.mosaic.array.max(),
                         clipped_layer.mosaic.array.percent(percentile))

    def test_scale(self):
        scaled_layer = self.layer.scale()
        self.assertEqual(scaled_layer.mosaic.dtype, Vips.BandFormat.UCHAR)
        self.assertEqual(scaled_layer.mosaic.array.max(), 255)
        self.assertEqual(scaled_layer.mosaic.array.min(), 0)

    def test_align(self):
        aligned_layer = ChannelLayer.create(
                            experiment=self.experiment,
                            tpoint_ix=0, channel_ix=0, zplane_ix=0, align=True)
        self.assertEqual(aligned_layer.mosaic.dtype, Vips.BandFormat.USHORT)
        self.assertEqual(aligned_layer.mosaic.dimensions,
                         self.layer.mosaic.dimensions)
        self.assertNotEqual(aligned_layer.mosaic.array,
                            self.layer.mosaic.array)

    def test_illumcorr(self):
        corrected_layer = ChannelLayer.create(
                            experiment=self.experiment,
                            tpoint_ix=0, channel_ix=0, zplane_ix=0,
                            illumcorr=True)
        self.assertEqual(corrected_layer.mosaic.dtype, Vips.BandFormat.USHORT)
        self.assertEqual(corrected_layer.mosaic.dimensions,
                         self.layer.mosaic.dimensions)
        self.assertNotEqual(corrected_layer.mosaic.array,
                            self.layer.mosaic.array)
