import unittest
from tmlib.tmaps.canonical import CanonicalWorkflowStepDescription
from tmlib.tmaps.canonical import CanonicalWorkflowStageDescription
from tmlib.tmaps.canonical import CanonicalWorkflowDescription
from tmlib.args import GeneralArgs
from tmlib.errors import WorkflowDescriptionError


class TestWorkflowStepDescription(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_initialize_with_correct_description_1(self):
        description = {
            'name': 'metaconfig',
            'args': dict()
        }
        step = CanonicalWorkflowStepDescription(**description)
        self.assertEqual(step.name, description['name'])
        self.assertNotEqual(dict(step)['args'], description['args'])
        self.assertIsInstance(step.args, GeneralArgs)

    def test_initialize_with_correct_description_2(self):
        description = {
            'name': 'metaconfig',
            'args': None
        }
        step = CanonicalWorkflowStepDescription(**description)
        self.assertEqual(step.name, description['name'])
        self.assertNotEqual(dict(step.args), description['args'])
        self.assertIsInstance(step.args, GeneralArgs)

    def test_initialize_with_correct_description_3(self):
        description = {
            'name': 'metaconfig',
            'args': {
                'file_format': 'cellvoyager'
            }
        }
        step = CanonicalWorkflowStepDescription(**description)
        self.assertEqual(step.name, description['name'])
        self.assertNotEqual(dict(step.args), description['args'])
        self.assertIsInstance(step.args, GeneralArgs)

    def test_initialize_with_incorrect_name(self):
        wrong_description = {
            'name': 'bla',
            'args': None
        }
        with self.assertRaises(WorkflowDescriptionError):
            CanonicalWorkflowStepDescription(**wrong_description)

    def test_initialize_with_incorrect_args_type_2(self):
        wrong_description = {
            'name': 'metaconfig',
            'args': [1, 2]
        }
        with self.assertRaises(TypeError):
            CanonicalWorkflowStepDescription(**wrong_description)

    def test_initialize_with_incorrect_args_type_3(self):
        wrong_description = {
            'name': 'metaconfig',
            'args': {1: 'blabla'}
        }
        with self.assertRaises(TypeError):
            CanonicalWorkflowStepDescription(**wrong_description)

    def test_initialize_with_incorrect_args_name(self):
        wrong_description = {
            'name': 'metaconfig',
            'args': {'bla': None}
        }
        with self.assertRaises(WorkflowDescriptionError):
            CanonicalWorkflowStepDescription(**wrong_description)

    def test_return_description(self):
        description = {
            'name': 'metaconfig',
            'args': {
                'file_format': 'cellvoyager'
            }
        }
        step = CanonicalWorkflowStepDescription(**description)
        step_dict = dict(step)
        self.assertIsInstance(step_dict, dict)
        self.assertEqual(step_dict['args']['file_format'],
                         description['args']['file_format'])


class TestWorkflowStageDescription(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_initialize_with_correct_description(self):
        description = {
            'name': 'image_conversion',
            'steps': [
                {
                    'name': 'metaextract',
                    'args': dict()
                },
                {
                    'name': 'metaconfig',
                    'args': dict()
                },
            ]
        }
        stage = CanonicalWorkflowStageDescription(**description)
        self.assertEqual(stage.name, description['name'])
        self.assertEqual(stage.steps[0].name, description['steps'][0]['name'])
        self.assertEqual(dict(stage.steps[0])['args'],
                         description['steps'][0]['args'])
        self.assertTrue(all(
            [isinstance(s, CanonicalWorkflowStepDescription) for s in stage.steps]
        ))

    def test_initialize_with_incorrect_steps_value(self):
        wrong_description = {
            'name': 'image_conversion',
            'steps': list()
        }
        with self.assertRaises(ValueError):
            CanonicalWorkflowStageDescription(**wrong_description)

    def test_initialize_with_incorrect_steps_type(self):
        wrong_description = {
            'name': 'image_conversion',
            'steps': [list()]
        }
        with self.assertRaises(TypeError):
            CanonicalWorkflowStageDescription(**wrong_description)

    def test_initialize_with_incorrect_name(self):
        wrong_description = {
            'name': 'bla',
            'steps': [
                {
                    'name': 'metaextract',
                    'args': dict()
                }
            ]
        }
        with self.assertRaises(WorkflowDescriptionError):
            CanonicalWorkflowStageDescription(**wrong_description)

    def test_initialize_with_incorrect_order(self):
        wrong_description = {
            'name': 'image_conversion',
            'steps': [
                {
                    'name': 'metaconfig',
                    'args': dict()
                },
                {
                    'name': 'metaextract',
                    'args': dict()
                }
            ]
        }
        with self.assertRaises(WorkflowDescriptionError):
            CanonicalWorkflowStageDescription(**wrong_description)

    def test_return_description(self):
        description = {
            'name': 'image_conversion',
            'steps': [
                {
                    'name': 'metaextract',
                    'args': dict()
                }
            ]
        }
        stage = CanonicalWorkflowStageDescription(**description)
        self.assertEqual(dict(stage)['steps'][0]['name'],
                         description['steps'][0]['name'])


class TestWorkflowDescription(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_initialize_with_correct_description(self):
        description = {
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
        workflow = CanonicalWorkflowDescription(**description)
        self.assertEqual(workflow.stages[0].name,
                         description['stages'][0]['name'])
        self.assertEqual(workflow.stages[0].steps[0].name,
                         description['stages'][0]['steps'][0]['name'])
        self.assertEqual(dict(workflow.stages[0].steps[0])['args'],
                         description['stages'][0]['steps'][0]['args'])
        self.assertTrue(all(
            [isinstance(s, CanonicalWorkflowStageDescription) for s in workflow.stages]
        ))

    def test_initialization_with_incorrect_name(self):
        wrong_description = {
            'bla': [
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
        with self.assertRaises(WorkflowDescriptionError):
            CanonicalWorkflowDescription(**wrong_description)

    def test_initialization_with_incorrect_type(self):
        wrong_description = {
            'stages':
                {
                    'name': 'image_conversion',
                    'steps': [
                        {
                            'name': 'metaextract',
                            'args': dict()
                        }
                    ]
                }
        }
        with self.assertRaises(TypeError):
            CanonicalWorkflowDescription(**wrong_description)

    def test_initialization_with_incorrect_argument(self):
        wrong_description = {
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
            ],
            'bla': None
        }
        with self.assertRaises(WorkflowDescriptionError):
            CanonicalWorkflowDescription(**wrong_description)

    def test_initialization_with_incorrect_order(self):
        wrong_description = {
            'stages': [
                {
                    'name': 'image_preprocessing',
                    'steps': [
                        {
                            'name': 'corilla',
                            'args': dict()
                        }
                    ]
                },
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
        with self.assertRaises(WorkflowDescriptionError):
            CanonicalWorkflowDescription(**wrong_description)

    def test_return_description(self):
        description = {
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
        workflow = CanonicalWorkflowDescription(**description)
        workflow_dict = dict(workflow)
        self.assertIsInstance(workflow_dict, dict)
        self.assertEqual(workflow_dict['stages'][0]['name'],
                         description['stages'][0]['name'])
