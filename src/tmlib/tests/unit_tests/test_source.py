import os
import fake_filesystem_unittest
from mock import PropertyMock
from mock import patch
import json
import bioformats
from cached_property import cached_property
from tmlib.source import PlateSource
from tmlib.source import PlateAcquisition
from tmlib.metadata import ImageFileMapping



class TestSourceSetup(fake_filesystem_unittest.TestCase):

    def setUp(self):
        self.setUpPyfakefs()
        self.data_location = '/testdir'
        os.mkdir(self.data_location)
        # Create an experiment on the fake file system
        self.experiment_name = 'testExperiment'
        self.experiment_dir = os.path.join(
                                self.data_location,
                                self.experiment_name)
        os.mkdir(self.experiment_dir)
        self.sources_dir = os.path.join(self.experiment_dir, 'sources')
        os.mkdir(self.sources_dir)
        self.plates_dir = os.path.join(self.experiment_dir, 'plates')
        self.layers_dir = os.path.join(self.experiment_dir, 'layers')
        # Add a plate with one acquisition
        self.plate_name = 'testPlate'
        self.source_dir = os.path.join(
                                self.sources_dir,
                                'plate_%s' % self.plate_name)
        os.mkdir(self.source_dir)
        self.acquisition_index = 0
        self.acquisition_dir = os.path.join(
                                self.source_dir,
                                'acquisition_%.2d' % self.acquisition_index)
        os.mkdir(self.acquisition_dir)

    def tearDown(self):
        self.tearDownPyfakefs()


class TestPlateSource(TestSourceSetup):

    @property
    def source(self):
        return PlateSource(self.source_dir)

    def _add_image_mapping_file(self):
        filename = os.path.join(self.source.dir,
                                self.source.image_mapping_file)
        with open(filename, 'w') as f:
            mapping = [{}]
            f.write(json.dumps(mapping))

    def test_initialize_platesource(self):
        self.assertEqual(self.source.dir, self.source_dir)
        self.assertEqual(self.source.name, self.plate_name)

    def test_list_acquisitions(self):
        self.assertEqual(len(self.source.acquisitions), 1)
        self.assertEqual(self.source.acquisitions[0].index, 0)

    def test_add_acquisition(self):
        acquisition = self.source.add_acquisition()
        self.assertIsInstance(acquisition, PlateAcquisition)
        self.assertEqual(len(self.source.acquisitions), 2)
        self.assertEqual(self.source.acquisitions[1].index, 1)

    def test_image_mapping(self):
        self._add_image_mapping_file()
        self.assertIsInstance(self.source.image_mapping, list)
        self.assertEqual(len(self.source.image_mapping), 1)
        self.assertIsInstance(self.source.image_mapping[0], ImageFileMapping)


class TestPlateAcquisitionDirectories(TestSourceSetup):

    @property
    def acquisition(self):
        return PlateAcquisition(self.acquisition_dir)

    def test_initialize_plateacquisition(self):
        self.assertEqual(self.acquisition.dir, self.acquisition_dir)
        self.assertEqual(self.acquisition.index, self.acquisition_index)

    def test_image_dir_attribute(self):
        image_dir = os.path.join(
                        self.acquisition.dir,
                        self.acquisition.IMAGE_DIR_NAME)
        self.assertFalse(os.path.exists(image_dir))
        self.assertEqual(self.acquisition.image_dir, image_dir)
        self.assertTrue(os.path.exists(image_dir))

    def test_metadata_dir_attribute(self):
        metadata_dir = os.path.join(
                        self.acquisition.dir,
                        self.acquisition.METADATA_DIR_NAME)
        self.assertFalse(os.path.exists(metadata_dir))
        self.assertEqual(self.acquisition.metadata_dir, metadata_dir)
        self.assertTrue(os.path.exists(metadata_dir))

    def test_omexml_dir_attribute(self):
        acquisition = PlateAcquisition(self.acquisition_dir)
        omexml_dir = os.path.join(
                        acquisition.dir, acquisition.OMEXML_DIR_NAME)
        self.assertFalse(os.path.exists(omexml_dir))
        self.assertEqual(acquisition.omexml_dir, omexml_dir)
        self.assertTrue(os.path.exists(omexml_dir))


class TestPlateAcquisitionFiles(TestSourceSetup):

    def _add_image_files(self, extension):
        # Add some image files to the acquisition
        self.image_files = list()

        for i in xrange(10):
            name = 'image_%.2d%s' % (i, extension)
            filename = os.path.join(self.acquisition.image_dir, name)
            with open(filename, 'w') as f:
                f.write('')
            self.image_files.append(name)

    def _add_additional_files(self):
        # Add an additional metadata file to the acquisition
        self.metadata_file = 'metadata.xml'
        filename = os.path.join(self.acquisition.metadata_dir,
                                self.metadata_file)
        with open(filename, 'w') as f:
            f.write('')

    def _add_metadata_file(self):
        filename = os.path.join(self.acquisition.dir,
                                self.acquisition.image_metadata_file)
        with open(filename, 'w') as f:
            # example from
            f.write(u'''<?xml version="1.0" encoding="UTF-8" standalone="no"?>
                <OME xmlns="http://www.openmicroscopy.org/Schemas/OME/2015-01" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.openmicroscopy.org/Schemas/OME/2015-01 http://www.openmicroscopy.org/Schemas/OME/2015-01/ome.xsd">
                   <Image ID="Image:0" Name="image_00.tif">
                   </Image>
                </OME>
            ''')

    def _add_image_mapping_file(self):
        filename = os.path.join(self.acquisition.dir,
                                self.acquisition.image_mapping_file)
        with open(filename, 'w') as f:
            mapping = [{}]
            f.write(json.dumps(mapping))

    @cached_property
    def acquisition(self):
        return PlateAcquisition(self.acquisition_dir)

    def test_image_files_1(self):
        self._add_image_files('.tif')
        # We need to mock the supported file extensions, because they would
        # be read from a file that doesn't exist
        # (and that we don't want to test here)
        with patch.object(
                    PlateAcquisition, '_supported_image_file_extensions',
                    new_callable=PropertyMock
                ) as mock_property:
            mocked_acquisition = PlateAcquisition(self.acquisition_dir)
            mock_property.return_value = {'.tif'}
            self.assertEqual(mocked_acquisition.image_files, self.image_files)

    def test_image_files_2(self):
        self._add_image_files('.png')
        # We need to mock the supported file extensions, because they would
        # be read from a file that doesn't exist
        # (and that we don't want to test here)
        with patch.object(
                    PlateAcquisition, '_supported_image_file_extensions',
                    new_callable=PropertyMock
                ) as mock_property:
            mocked_acquisition = PlateAcquisition(self.acquisition_dir)
            mock_property.return_value = {'.tif'}
            with self.assertRaises(OSError):
                mocked_acquisition.image_files

    def test_additional_files(self):
        self._add_additional_files()
        self.assertEqual(self.acquisition.additional_files,
                         [self.metadata_file])

    def test_image_metadata(self):
        self._add_metadata_file()
        self.assertIsInstance(self.acquisition.image_metadata,
                              bioformats.OMEXML)

    def test_image_mapping(self):
        self._add_image_mapping_file()
        self.assertIsInstance(self.acquisition.image_mapping, list)
        self.assertEqual(len(self.acquisition.image_mapping), 1)
        self.assertIsInstance(self.acquisition.image_mapping[0],
                              ImageFileMapping)
