import os
import fake_filesystem_unittest
from tmlib.cfg import UserConfiguration
from tmlib.errors import WorkflowDescriptionError


class TestUserConfiguration(fake_filesystem_unittest.TestCase):

    def setUp(self):
        self.setUpPyfakefs()
        self.data_location = '/testdir'
        os.mkdir(self.data_location)
        experiment_name = '150820-Testset-CV'
        self.experiment_dir = os.path.join(self.data_location, experiment_name)
        os.mkdir(self.experiment_dir)  # on the fake filesystem
        self.plate_format = 384

    def tearDown(self):
        self.tearDownPyfakefs()

    def test_initialize_without_setting_directories(self):
        config_settings = {
            'sources_dir': None,
            'plates_dir': None,
            'layers_dir': None,
            'plate_format': self.plate_format
        }
        config = UserConfiguration(
            experiment_dir=self.experiment_dir, **config_settings
        )
        self.assertEqual(config.plate_format, self.plate_format)
        expected_sources_dir = os.path.join(self.experiment_dir, 'sources')
        self.assertEqual(config.sources_dir, expected_sources_dir)
        expected_plates_dir = os.path.join(self.experiment_dir, 'plates')
        self.assertEqual(config.plates_dir, expected_plates_dir)
        expected_layers_dir = os.path.join(self.experiment_dir, 'layers')
        self.assertEqual(config.layers_dir, expected_layers_dir)

    def test_initialize_with_setting_directories(self):
        expected_sources_dir = os.path.join(self.data_location, 'sources')
        expected_plates_dir = os.path.join(self.data_location, 'plates')
        expected_layers_dir = os.path.join(self.data_location, 'layers')
        config_settings = {
                'sources_dir': expected_sources_dir,
                'plates_dir': expected_plates_dir,
                'layers_dir': expected_layers_dir,
                'plate_format': self.plate_format
            }
        config = UserConfiguration(
            experiment_dir=self.experiment_dir, **config_settings
        )
        self.assertEqual(config.plate_format, self.plate_format)
        self.assertEqual(config.sources_dir, expected_sources_dir)
        self.assertEqual(config.plates_dir, expected_plates_dir)
        self.assertEqual(config.layers_dir, expected_layers_dir)

    def test_initialize_with_correct_workflow_description(self):
        config_settings = {
            'sources_dir': None,
            'plates_dir': None,
            'layers_dir': None,
            'plate_format': self.plate_format,
            'workflow': {
                'type': 'canonical',
                'stages': [
                    {
                        'name': 'image_conversion',
                        'steps': [
                            {
                                'name': 'metaextract',
                                'args': dict()
                            }
                        ]
                    }
                ]
            }
        }
        config = UserConfiguration(
            experiment_dir=self.experiment_dir, **config_settings
        )
        self.assertEqual(config.workflow.stages[0].name,
                         config_settings['workflow']['stages'][0]['name'])
        self.assertEqual(config.workflow.stages[0].steps[0].name,
                         config_settings['workflow']['stages'][0]['steps'][0]['name'])

    def test_initialize_with_incorrect_workflow_description(self):
        config_settings = {
            'sources_dir': None,
            'plates_dir': None,
            'layers_dir': None,
            'plate_format': self.plate_format,
            'workflow': {
                'type': 'bla',
                'stages': [
                    {
                        'name': 'image_conversion',
                        'steps': [
                            {
                                'name': 'metaextract',
                                'args': dict()
                            }
                        ]
                    }
                ]
            }
        }
        with self.assertRaises(WorkflowDescriptionError):
            UserConfiguration(
                experiment_dir=self.experiment_dir, **config_settings
            )

    def test_to_dict(self):
        expected_sources_dir = os.path.join(self.data_location, 'sources')
        expected_plates_dir = os.path.join(self.data_location, 'plates')
        expected_layers_dir = os.path.join(self.data_location, 'layers')
        config_settings = {
            'sources_dir': expected_sources_dir,
            'plates_dir': expected_plates_dir,
            'layers_dir': expected_layers_dir,
            'plate_format': self.plate_format,
            'workflow': {
                'type': 'canonical',
                'stages': [
                    {
                        'name': 'image_conversion',
                        'steps': [
                            {
                                'name': 'metaextract',
                                'args': dict()
                            }
                        ]
                    }
                ]
            }
        }
        config = UserConfiguration(
            experiment_dir=self.experiment_dir, **config_settings
        )
        self.assertIsInstance(dict(config), dict)

    def test_dump_to_file(self):
        expected_sources_dir = os.path.join(self.data_location, 'sources')
        expected_plates_dir = os.path.join(self.data_location, 'plates')
        expected_layers_dir = os.path.join(self.data_location, 'layers')
        config_settings = {
            'sources_dir': expected_sources_dir,
            'plates_dir': expected_plates_dir,
            'layers_dir': expected_layers_dir,
            'plate_format': self.plate_format,
            'workflow': {
                'type': 'canonical',
                'stages': [
                    {
                        'name': 'image_conversion',
                        'steps': [
                            {
                                'name': 'metaextract',
                                'args': dict()
                            }
                        ]
                    }
                ]
            }
        }
        config = UserConfiguration(
            experiment_dir=self.experiment_dir, **config_settings
        )
        self.assertFalse(os.path.exists(config.cfg_file))
        config.dump_to_file()
        self.assertTrue(os.path.exists(config.cfg_file))
