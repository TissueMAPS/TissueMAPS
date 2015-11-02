import os
import fake_filesystem_unittest
from tmlib import cfg
from tmlib.source import PlateSource
from tmlib.source import PlateAcquisition


class TestSource(fake_filesystem_unittest.TestCase):

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
        # Add user configuration settings file
        self.user_cfg_settings = {
            'sources_dir': self.sources_dir,
            'plates_dir': self.plates_dir,
            'layers_dir': self.layers_dir,
            'plate_format': 384,
        }
        self.user_cfg = cfg.UserConfiguration(
                        experiment_dir=self.experiment_dir,
                        cfg_settings=self.user_cfg_settings)

    def tearDown(self):
        self.tearDownPyfakefs()


class TestPlateSource(TestSource):

    def test_initialize_platesource(self):
        source = PlateSource(self.source_dir, user_cfg=self.user_cfg)
        self.assertEqual(source.dir, self.source_dir)
        self.assertEqual(source.name, self.plate_name)
        self.assertEqual(source.user_cfg.sources_dir, self.sources_dir)

    def test_list_acquisitions(self):
        source = PlateSource(self.source_dir, user_cfg=self.user_cfg)
        self.assertEqual(len(source.acquisitions), 1)
        self.assertEqual(source.acquisitions[0].index, 0)

    def test_add_acquisition(self):
        source = PlateSource(self.source_dir, user_cfg=self.user_cfg)
        acquisition = source.add_acquisition()
        self.assertIsInstance(acquisition, PlateAcquisition)
        self.assertEqual(len(source.acquisitions), 2)
        self.assertEqual(source.acquisitions[1].index, 1)


class TestPlateAcquisition(TestSource):

    @property
    def acquisition(self):
        return PlateAcquisition(self.acquisition_dir, user_cfg=self.user_cfg)

    def test_initialize_plateacquisition(self):
        self.assertEqual(self.acquisition.dir, self.acquisition_dir)
        self.assertEqual(self.acquisition.index, self.acquisition_index)
        self.assertEqual(self.acquisition.user_cfg.sources_dir,
                         self.sources_dir)

    def test_image_dir_attribute(self):
        acquisition = PlateAcquisition(self.acquisition_dir,
                                       user_cfg=self.user_cfg)
        image_dir = os.path.join(acquisition.dir, acquisition.IMAGE_DIR_NAME)
        self.assertFalse(os.path.exists(image_dir))
        self.assertEqual(acquisition.image_dir, image_dir)
        self.assertTrue(os.path.exists(image_dir))

    def test_metadata_dir_attribute(self):
        acquisition = PlateAcquisition(self.acquisition_dir,
                                       user_cfg=self.user_cfg)
        metadata_dir = os.path.join(
                        acquisition.dir, acquisition.METADATA_DIR_NAME)
        self.assertFalse(os.path.exists(metadata_dir))
        self.assertEqual(acquisition.metadata_dir, metadata_dir)
        self.assertTrue(os.path.exists(metadata_dir))

    def test_omexml_dir_attribute(self):
        acquisition = PlateAcquisition(self.acquisition_dir,
                                       user_cfg=self.user_cfg)
        omexml_dir = os.path.join(
                        acquisition.dir, acquisition.OMEXML_DIR_NAME)
        self.assertFalse(os.path.exists(omexml_dir))
        self.assertEqual(acquisition.omexml_dir, omexml_dir)
        self.assertTrue(os.path.exists(omexml_dir))
