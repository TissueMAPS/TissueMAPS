# -*- coding: utf-8 -*-
import bioformats
import unittest
from tmlib.metadata import ChannelImageMetadata
from tmlib.metadata import IllumstatsImageMetadata
from tmlib.metadata import MosaicMetadata


class TestChannelImageMetadata(unittest.TestCase):

    def setUp(self):
        omexml = u'''<?xml version="1.0" encoding="UTF-8" standalone="no"?>
            <OME xmlns="http://www.openmicroscopy.org/Schemas/OME/2015-01" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.openmicroscopy.org/Schemas/OME/2015-01 http://www.openmicroscopy.org/Schemas/OME/2015-01/ome.xsd">
               <Image ID="Image:0" Name="test_t000_D03_y000_x000_c000_z000.png">
                  <AcquisitionDate>2015-08-20T18:32:41.223+02:00</AcquisitionDate>
                  <Pixels DimensionOrder="XYCTZ" ID="ffc195b6-9a12-4908-87e2-7d6fbf69d625" SizeC="1" SizeT="1" SizeX="2560" SizeY="2160" SizeZ="1" Type="uint16">
                    <Channel ID="Channel1:0" Name="1" SamplesPerPixel="1" />
                    <Plane PositionX="-458.3" PositionY="248.2" TheC="0" TheT="0" TheZ="0" />
                  </Pixels>
               </Image>
            </OME>
        '''
        bf_metadata = bioformats.OMEXML(omexml)
        self.image_element = bf_metadata.image(0)

    def tearDown(self):
        pass

    def test_initialiaze(self):
        metadata = ChannelImageMetadata()
        self.assertEqual(metadata.x_shift, 0)
        self.assertEqual(metadata.y_shift, 0)
        self.assertEqual(metadata.upper_overhang, 0)
        self.assertEqual(metadata.lower_overhang, 0)
        self.assertEqual(metadata.left_overhang, 0)
        self.assertEqual(metadata.right_overhang, 0)
        self.assertEqual(metadata.is_aligned, False)
        self.assertEqual(metadata.is_corrected, False)
        self.assertEqual(metadata.is_omitted, False)

    def test_initialize_with_arguments(self):
        args = {
            'id': 0,
            'name': 'image_test',
            'plate_name': 'plate_test',
            'well_name': 'A01',
            'channel_ix': 0,
            'zplane_ix': 0,
            'tpoint_ix': 0,
            'channel_name': 'channel_test',
            'well_pos_x': 0,
            'well_pos_y': 0,
            'site_ix': 0
        }
        metadata = ChannelImageMetadata(**args)
        self.assertEqual(metadata.id, 0)

    def test_initialize_with_insufficient_arguments(self):
        args = {
            'id': 0,
            'name': 'image_test'
        }
        with self.assertRaises(ValueError):
            ChannelImageMetadata(**args)

    def test_id_attribute(self):
        metadata = ChannelImageMetadata()
        metadata.id = 0
        self.assertIsInstance(metadata.id, int)
        self.assertEqual(metadata.id, 0)

    def test_id_attribute_wrong_datatype(self):
        metadata = ChannelImageMetadata()
        with self.assertRaises(TypeError):
            metadata.id = float(0)

    def test_name_attribute(self):
        metadata = ChannelImageMetadata()
        self.assertFalse(hasattr(metadata, 'name'))
        metadata.name = 'test_t000_D03_y000_x000_c000_z000.png'
        self.assertIsInstance(metadata.name, str)
        self.assertEqual(metadata.name, 'test_t000_D03_y000_x000_c000_z000.png')

    def test_name_attribute_unicode(self):
        metadata = ChannelImageMetadata()
        metadata.name = u'test_t000_D03_y000_x000_c000_z000.png'
        self.assertIsInstance(metadata.name, str)
        self.assertEqual(metadata.name, 'test_t000_D03_y000_x000_c000_z000.png')

    def test_name_attribute_wrong_datatype(self):
        metadata = ChannelImageMetadata()
        with self.assertRaises(TypeError):
            metadata.name = 10

    def test_site_ix_attribute(self):
        metadata = ChannelImageMetadata()
        self.assertFalse(hasattr(metadata, 'site_ix'))
        metadata.site_ix = 0
        self.assertIsInstance(metadata.site_ix, int)
        self.assertEqual(metadata.site_ix, 0)

    def test_site_ix_attribute_wrong_datatype(self):
        metadata = ChannelImageMetadata()
        with self.assertRaises(TypeError):
            metadata.site_ix = float(0)

    def test_tpoint_ix_attribute(self):
        metadata = ChannelImageMetadata()
        self.assertFalse(hasattr(metadata, 'tpoint_ix'))
        metadata.tpoint_ix = 0
        self.assertIsInstance(metadata.tpoint_ix, int)
        self.assertEqual(metadata.tpoint_ix, 0)

    def test_tpoint_ix_attribute_wrong_datatype(self):
        metadata = ChannelImageMetadata()
        with self.assertRaises(TypeError):
            metadata.tpoint_ix = float(0)

    def test_channel_ix_attribute(self):
        metadata = ChannelImageMetadata()
        self.assertFalse(hasattr(metadata, 'channel_ix'))
        metadata.channel_ix = 0
        self.assertIsInstance(metadata.channel_ix, int)
        self.assertEqual(metadata.channel_ix, 0)

    def test_channel_ix_attribute_wrong_datatype(self):
        metadata = ChannelImageMetadata()
        with self.assertRaises(TypeError):
            metadata.channel_ix = float(0)

    def test_zplane_ix_attribute(self):
        metadata = ChannelImageMetadata()
        self.assertFalse(hasattr(metadata, 'zplane_ix'))
        metadata.zplane_ix = 0
        self.assertIsInstance(metadata.zplane_ix, int)
        self.assertEqual(metadata.zplane_ix, 0)

    def test_zplane_ix_attribute_wrong_datatype(self):
        metadata = ChannelImageMetadata()
        with self.assertRaises(TypeError):
            metadata.zplane_ix = float(0)

    def test_well_name_attribute(self):
        metadata = ChannelImageMetadata()
        self.assertFalse(hasattr(metadata, 'plate_name'))
        metadata.well_name = 'plate_test'
        self.assertIsInstance(metadata.well_name, str)
        self.assertEqual(metadata.well_name, 'plate_test')

    def test_well_name_attribute_unicode(self):
        metadata = ChannelImageMetadata()
        self.assertFalse(hasattr(metadata, 'well_name'))
        metadata.well_name = u'well_name'
        self.assertIsInstance(metadata.well_name, str)
        self.assertEqual(metadata.well_name, 'well_name')

    def test_well_name_attribute_wrong_datatype(self):
        metadata = ChannelImageMetadata()
        with self.assertRaises(TypeError):
            metadata.well_name = 0

    def test_well_pos_x_attribute_1(self):
        metadata = ChannelImageMetadata()
        metadata.well_pos_x = 0
        self.assertIsInstance(metadata.well_pos_x, int)
        self.assertEqual(metadata.well_pos_x, 0)

    def test_well_pos_x_attribute_wrong_datatype_1(self):
        metadata = ChannelImageMetadata()
        with self.assertRaises(TypeError):
            metadata.well_pos_x = float(0)

    def test_well_pos_x_attribute_wrong_datatype(self):
        metadata = ChannelImageMetadata()
        with self.assertRaises(TypeError):
            metadata.well_pos_x = '0'

    def test_well_pos_y_attribute(self):
        metadata = ChannelImageMetadata()
        metadata.well_pos_y = 0
        self.assertIsInstance(metadata.well_pos_y, int)
        self.assertEqual(metadata.well_pos_y, 0)

    def test_well_pos_y_attribute_wrong_datatype_1(self):
        metadata = ChannelImageMetadata()
        with self.assertRaises(TypeError):
            metadata.well_pos_y = float(0)

    def test_well_pos_y_attribute_wrong_datatype_2(self):
        metadata = ChannelImageMetadata()
        with self.assertRaises(TypeError):
            metadata.well_pos_y = '0'

    def test_upper_overhang_attribute(self):
        metadata = ChannelImageMetadata()
        self.assertEqual(metadata.upper_overhang, 0)
        metadata.upper_overhang = 10
        self.assertEqual(metadata.upper_overhang, 10)

    def test_upper_overhang_attribute_wrong_datatype(self):
        metadata = ChannelImageMetadata()
        with self.assertRaises(TypeError):
            metadata.upper_overhang = float(0)

    def test_lower_overhang_attribute(self):
        metadata = ChannelImageMetadata()
        self.assertEqual(metadata.lower_overhang, 0)
        metadata.lower_overhang = 10
        self.assertEqual(metadata.lower_overhang, 10)

    def test_lower_overhang_attribute_wrong_datatype(self):
        metadata = ChannelImageMetadata()
        with self.assertRaises(TypeError):
            metadata.lower_overhang = float(0)

    def test_right_overhang_attribute(self):
        metadata = ChannelImageMetadata()
        self.assertEqual(metadata.right_overhang, 0)
        metadata.right_overhang = 10
        self.assertEqual(metadata.right_overhang, 10)

    def test_right_overhang_attribute_wrong_datatype(self):
        metadata = ChannelImageMetadata()
        with self.assertRaises(TypeError):
            metadata.right_overhang = float(0)

    def test_left_overhang_attribute(self):
        metadata = ChannelImageMetadata()
        self.assertEqual(metadata.left_overhang, 0)
        metadata.left_overhang = 10
        self.assertEqual(metadata.left_overhang, 10)

    def test_left_overhang_attribute_wrong_datatype(self):
        metadata = ChannelImageMetadata()
        with self.assertRaises(TypeError):
            metadata.left_overhang = float(0)

    def test_x_shift_attribute(self):
        metadata = ChannelImageMetadata()
        self.assertEqual(metadata.x_shift, 0)
        metadata.x_shift = 10
        self.assertEqual(metadata.x_shift, 10)

    def test_y_shift_attribute(self):
        metadata = ChannelImageMetadata()
        self.assertEqual(metadata.y_shift, 0)
        metadata.y_shift = 10
        self.assertEqual(metadata.y_shift, 10)

    def test_is_omitted_attribute(self):
        metadata = ChannelImageMetadata()
        self.assertFalse(metadata.is_omitted)
        metadata.is_omitted = True
        self.assertTrue(metadata.is_omitted)
        metadata.is_omitted = False
        self.assertFalse(metadata.is_omitted)

    def test_is_corrected_attribute(self):
        metadata = ChannelImageMetadata()
        self.assertFalse(metadata.is_corrected)
        metadata.is_corrected = True
        self.assertTrue(metadata.is_corrected)
        metadata.is_corrected = False
        self.assertFalse(metadata.is_corrected)

    def test_is_aligned_attribute(self):
        metadata = ChannelImageMetadata()
        self.assertFalse(metadata.is_aligned)
        metadata.is_aligned = True
        self.assertTrue(metadata.is_aligned)
        metadata.is_aligned = False
        self.assertFalse(metadata.is_aligned)

    def test_to_dict_1(self):
        metadata = ChannelImageMetadata()
        metadata.id = 0
        metadata.name = 'test'
        with self.assertRaises(AttributeError):
            dict(metadata)

    def test_to_dict_2(self):
        args = {
            'id': 0,
            'name': 'image_test',
            'plate_name': 'plate_test',
            'well_name': 'A01',
            'channel_ix': 0,
            'zplane_ix': 0,
            'tpoint_ix': 0,
            'channel_name': 'channel_test',
            'well_pos_x': 0,
            'well_pos_y': 0,
            'site_ix': 0
        }
        metadata = ChannelImageMetadata(**args)
        metadata_as_dict = dict(metadata)
        for k, v in args.iteritems():
            self.assertEqual(getattr(metadata, k), metadata_as_dict[k])


class TestIllumstatsImageMetadata(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_filename_attribute_1(self):
        metadata = IllumstatsImageMetadata()
        self.assertFalse(hasattr(metadata, 'filename'))
        metadata.filename = 'image_test'
        self.assertEqual(metadata.filename, 'image_test')

    def test_filename_attribute_2(self):
        metadata = IllumstatsImageMetadata()
        metadata.filename = u'image_test'
        self.assertIsInstance(metadata.filename, str)
        self.assertEqual(metadata.filename, 'image_test')

    def test_tpoint_ix_attribute(self):
        metadata = IllumstatsImageMetadata()
        self.assertFalse(hasattr(metadata, 'tpoint_ix'))
        metadata.tpoint_ix = 0
        self.assertIsInstance(metadata.tpoint_ix, int)
        self.assertEqual(metadata.tpoint_ix, 0)

    def test_tpoint_ix_attribute_wrong_datatype(self):
        metadata = IllumstatsImageMetadata()
        with self.assertRaises(TypeError):
            metadata.tpoint_ix = float(0)

    def test_channel_ix_attribute(self):
        metadata = IllumstatsImageMetadata()
        self.assertFalse(hasattr(metadata, 'channel_ix'))
        metadata.channel_ix = 0
        self.assertIsInstance(metadata.channel_ix, int)
        self.assertEqual(metadata.channel_ix, 0)

    def test_channel_ix_attribute_wrong_datatype(self):
        metadata = IllumstatsImageMetadata()
        with self.assertRaises(TypeError):
            metadata.channel_ix = float(0)


class TestMosaicMetadata(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_name_attribute(self):
        metadata = MosaicMetadata()
        self.assertFalse(hasattr(metadata, 'name'))
        metadata.name = 'mosaic_test'
        self.assertIsInstance(metadata.name, str)
        self.assertEqual(metadata.name, 'mosaic_test')

    def test_name_attribute_unicode(self):
        metadata = MosaicMetadata()
        metadata.name = u'mosaic_test'
        self.assertIsInstance(metadata.name, str)
        self.assertEqual(metadata.name, 'mosaic_test')

    def test_name_attribute_wrong_datatype(self):
        metadata = MosaicMetadata()
        with self.assertRaises(TypeError):
            metadata.name = 10

    def test_tpoint_ix_attribute(self):
        metadata = MosaicMetadata()
        self.assertFalse(hasattr(metadata, 'tpoint_ix'))
        metadata.tpoint_ix = 0
        self.assertIsInstance(metadata.tpoint_ix, int)
        self.assertEqual(metadata.tpoint_ix, 0)

    def test_tpoint_ix_attribute_wrong_datatype(self):
        metadata = MosaicMetadata()
        with self.assertRaises(TypeError):
            metadata.tpoint_ix = float(0)

    def test_channel_ix_attribute(self):
        metadata = MosaicMetadata()
        self.assertFalse(hasattr(metadata, 'channel_ix'))
        metadata.channel_ix = 0
        self.assertIsInstance(metadata.channel_ix, int)
        self.assertEqual(metadata.channel_ix, 0)

    def test_channel_ix_attribute_wrong_datatype(self):
        metadata = MosaicMetadata()
        with self.assertRaises(TypeError):
            metadata.channel_ix = float(0)

    def test_zplane_ix_attribute(self):
        metadata = MosaicMetadata()
        self.assertFalse(hasattr(metadata, 'zplane_ix'))
        metadata.zplane_ix = 0
        self.assertIsInstance(metadata.zplane_ix, int)
        self.assertEqual(metadata.zplane_ix, 0)

    def test_zplane_ix_attribute_wrong_datatype(self):
        metadata = MosaicMetadata()
        with self.assertRaises(TypeError):
            metadata.zplane_ix = float(0)

    def test_site_ixs_attribute(self):
        metadata = MosaicMetadata()
        self.assertFalse(hasattr(metadata, 'site_ixs'))
        metadata.site_ixs = [0, 1, 2]
        self.assertEqual(metadata.site_ixs, [0, 1, 2])

    def test_site_ixs_attribute_wrong_datatype_1(self):
        metadata = MosaicMetadata()
        with self.assertRaises(TypeError):
            metadata.site_ixs = 0

    def test_site_ixs_attribute_wrong_datatype_2(self):
        metadata = MosaicMetadata()
        with self.assertRaises(TypeError):
            metadata.site_ixs = ['0', '1', '2']

    def test_filenames_attribute_1(self):
        metadata = MosaicMetadata()
        self.assertFalse(hasattr(metadata, 'filenames'))
        metadata.filenames = ['a', 'b', 'c']
        self.assertEqual(metadata.filenames, ['a', 'b', 'c'])

    def test_filenames_attribute_2(self):
        metadata = MosaicMetadata()
        metadata.filenames = [u'a', u'b', u'c']
        self.assertEqual(metadata.filenames, ['a', 'b', 'c'])

    def test_filenames_attribute_wrong_datatype_1(self):
        metadata = MosaicMetadata()
        with self.assertRaises(TypeError):
            metadata.filenames = 'a'

    def test_filenames_attribute_wrong_datatype_2(self):
        metadata = MosaicMetadata()
        with self.assertRaises(TypeError):
            metadata.filenames = [0, 1, 2]
