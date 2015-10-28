import os
import unittest
import fake_filesystem_unittest
from tmlib.cfg import WorkflowStepDescription
from tmlib.cfg import WorkflowStageDescription
from tmlib.cfg import WorkflowDescription
from tmlib.cfg import UserConfiguration


class TestWorkflowStepDescription(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_initialize_with_description(self):
        description = {
            'name': 'bla',
            'args': dict()
        }
        step = WorkflowStepDescription(description=description)
        self.assertEqual(step.name, description['name'])
        self.assertEqual(step.args, description['args'])

        wrong_description = {
            'name': 'bla',
            'args': list()
        }
        with self.assertRaises(TypeError):
            WorkflowStepDescription(description=wrong_description)

        wrong_description = {
            'name': 1,
            'args': list()
        }
        with self.assertRaises(TypeError):
            WorkflowStepDescription(description=wrong_description)

        wrong_description = {
            'name': 'bla',
            'args': {1: 'blabla'}
        }
        with self.assertRaises(TypeError):
            WorkflowStepDescription(description=wrong_description)

        wrong_description = {
            'name': 'bla',
            'args': {'blabla': None}
        }
        with self.assertRaises(ValueError):
            WorkflowStepDescription(description=wrong_description)

    def test_return_description(self):
        description = {
            'name': 'bla',
            'args': dict()
        }
        step = WorkflowStepDescription(description=description)
        self.assertEqual(dict(step), description)


class TestWorkflowStageDescription(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_initialize_with_description(self):
        description = {
            'name': 'bla',
            'steps': [
                {
                    'name': 'bla',
                    'args': dict()
                }
            ]
        }
        stage = WorkflowStageDescription(description=description)
        self.assertEqual(stage.name, description['name'])
        self.assertEqual(stage.steps[0].name, description['steps'][0]['name'])
        self.assertEqual(stage.steps[0].args, description['steps'][0]['args'])
        self.assertTrue(all(
            [isinstance(s, WorkflowStepDescription) for s in stage.steps]
        ))

        wrong_description = {
            'name': 'bla',
            'steps': list()
        }
        with self.assertRaises(ValueError):
            WorkflowStageDescription(description=wrong_description)

        wrong_description = {
            'name': 'bla',
            'steps': ['blabla']
        }
        with self.assertRaises(TypeError):
            WorkflowStageDescription(description=wrong_description)

    def test_return_description(self):
        description = {
            'name': 'bla',
            'steps': [
                {
                    'name': 'bla',
                    'args': dict()
                }
            ]
        }
        stage = WorkflowStageDescription(description=description)
        self.assertEqual(dict(stage), description)


class TestWorkflowDescription(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_initialize_with_description(self):
        description = {
            'stages': [
                {
                    'name': 'bla',
                    'steps': [
                        {
                            'name': 'blabla',
                            'args': dict()
                        }
                    ]
                }
            ]
        }
        workflow = WorkflowDescription(description=description)
        self.assertEqual(workflow.stages[0].name,
                         description['stages'][0]['name'])
        self.assertEqual(workflow.stages[0].steps[0].name,
                         description['stages'][0]['steps'][0]['name'])
        self.assertEqual(workflow.stages[0].steps[0].args,
                         description['stages'][0]['steps'][0]['args'])
        self.assertTrue(all(
            [isinstance(s, WorkflowStageDescription) for s in workflow.stages]
        ))

        wrong_description = {
            'bla': [
                {
                    'name': 'bla',
                    'steps': [
                        {
                            'name': 'blabla',
                            'args': dict()
                        }
                    ]
                }
            ]
        }
        with self.assertRaises(KeyError):
            WorkflowDescription(description=wrong_description)

        wrong_description = {
            'stages':
                {
                    'name': 'bla',
                    'steps': [
                        {
                            'name': 'blabla',
                            'args': dict()
                        }
                    ]
                }
        }
        with self.assertRaises(TypeError):
            WorkflowDescription(description=wrong_description)

    def test_return_description(self):
        description = {
            'stages': [
                {
                    'name': 'bla',
                    'steps': [
                        {
                            'name': 'blabla',
                            'args': dict()
                        }
                    ]
                }
            ]
        }
        workflow = WorkflowDescription(description=description)
        self.assertEqual(dict(workflow), description)


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

    def test_initialization_without_setting_directories(self):
        config_settings = {
            'sources_dir': None,
            'plates_dir': None,
            'layers_dir': None,
            'plate_format': self.plate_format
        }
        config = UserConfiguration(
            experiment_dir=self.experiment_dir,
            cfg_settings=config_settings
        )
        self.assertEqual(config.plate_format, self.plate_format)
        expected_sources_dir = os.path.join(self.experiment_dir, 'sources')
        self.assertEqual(config.sources_dir, expected_sources_dir)
        expected_plates_dir = os.path.join(self.experiment_dir, 'plates')
        self.assertEqual(config.plates_dir, expected_plates_dir)
        expected_layers_dir = os.path.join(self.experiment_dir, 'layers')
        self.assertEqual(config.layers_dir, expected_layers_dir)

    def test_initialization_with_setting_directories(self):
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
            experiment_dir=self.experiment_dir,
            cfg_settings=config_settings
        )
        self.assertEqual(config.plate_format, self.plate_format)
        self.assertEqual(config.sources_dir, expected_sources_dir)
        self.assertEqual(config.plates_dir, expected_plates_dir)
        self.assertEqual(config.layers_dir, expected_layers_dir)

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
                'stages': [
                    {
                        'name': 'bla',
                        'steps': [
                            {
                                'name': 'blabla',
                                'args': dict()
                            }
                        ]
                    }
                ]
            }
        }
        config = UserConfiguration(
            experiment_dir=self.experiment_dir,
            cfg_settings=config_settings
        )
        self.assertEqual(dict(config), config_settings)
