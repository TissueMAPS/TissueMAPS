import os
import yaml
import fake_filesystem_unittest
from tmlib import cfg
from tmlib.experiment import Experiment


class TestExperiment(fake_filesystem_unittest.TestCase):

    def setUp(self):
        self.setUpPyfakefs()
        self.data_location = '/testdir'
        os.mkdir(self.data_location)
        # Create an experiment on the fake file system
        self.experiment_name = 'testExperiment'
        self.experiment_dir = os.path.join(
                                self.data_location,
                                self.experiment_name)
        os.mkdir(self.experiment_dir)  # on the fake filesystem
        # Create directory for uploaded files
        self.sources_dir = os.path.join(self.experiment_dir, 'sources')
        os.mkdir(self.sources_dir)
        # Add one uploaded plate with one acquisition
        self.plate_source_name = 'testPlate'
        self.plate_source_dir = os.path.join(
                                self.sources_dir,
                                'plate_%s' % self.plate_source_name)
        os.mkdir(self.plate_source_dir)
        self.acquisition_index = 0
        self.acquisition_dir = os.path.join(
                                self.plate_source_dir,
                                'acquisition_%.2d' % self.acquisition_index)
        os.mkdir(self.acquisition_dir)
        # Create directory for extracted files
        self.plates_dir = os.path.join(self.experiment_dir, 'plates')
        os.mkdir(self.plates_dir)
        # Add one plate with one cycle
        self.plate_name = self.plate_source_name
        self.plate_dir = os.path.join(
                                self.plates_dir,
                                'plate_%s' % self.plate_name)
        os.mkdir(self.plate_dir)
        self.cycle_index = 0
        self.cycle_dir = os.path.join(
                                self.plate_dir,
                                'cycle_%.2d' % self.cycle_index)
        os.mkdir(self.cycle_dir)
        # Create directory for created pyramids
        self.layers_dir = os.path.join(self.experiment_dir, 'layers')
        os.mkdir(self.layers_dir)
        # Create a data file
        self.data_file = 'data.h5'
        # Create a user configuration settings file
        self.user_cfg_settings = {
            'sources_dir': self.sources_dir,
            'plates_dir': self.plates_dir,
            'layers_dir': self.layers_dir,
            'plate_format': 384,
            'workflow': {
                'stages': [
                    {
                        'name': 'bla',
                        'steps': [
                            {
                                'name': 'metaconfig',
                                'args': dict()
                            }
                        ]
                    }
                ]
            }
        }
        user_cfg_filename = cfg.USER_CFG_FILE_FORMAT.format(
                    experiment_dir=self.experiment_dir, sep=os.path.sep)
        with open(user_cfg_filename, 'w') as f:
            f.write(
                yaml.dump(
                        self.user_cfg_settings,
                        default_flow_style=False,
                        explicit_start=True)
            )

    def tearDown(self):
        self.tearDownPyfakefs()

    def _test_basic_attributes(self, exp):
        self.assertEqual(exp.dir, self.experiment_dir)
        self.assertEqual(exp.name, self.experiment_name)
        self.assertEqual(exp.sources_dir, self.sources_dir)
        self.assertEqual(exp.plates_dir, self.plates_dir)
        self.assertEqual(exp.layers_dir, self.layers_dir)
        self.assertEqual(exp.data_file, self.data_file)
        self.assertEqual(dict(exp.user_cfg), self.user_cfg_settings)

    def test_initialize_experiment_without_user_cfg(self):
        exp = Experiment(self.experiment_dir)
        self._test_basic_attributes(exp)
        self.assertEqual(exp.library, 'vips')

    def test_initialize_experiment_with_user_cfg(self):
        user_cfg = cfg.UserConfiguration(
                        experiment_dir=self.experiment_dir,
                        cfg_settings=self.user_cfg_settings)
        exp = Experiment(self.experiment_dir, user_cfg=user_cfg)
        self._test_basic_attributes(exp)
        self.assertEqual(exp.library, 'vips')

    def test_initialize_experiment_with_library(self):
        exp = Experiment(self.experiment_dir, library='vips')
        self._test_basic_attributes(exp)
        self.assertEqual(exp.library, 'vips')
        exp = Experiment(self.experiment_dir, library='numpy')
        self._test_basic_attributes(exp)
        self.assertEqual(exp.library, 'numpy')
        with self.assertRaises(ValueError):
            Experiment(self.experiment_dir, library='bla')

    def test_experiment_sources_attribute(self):
        exp = Experiment(self.experiment_dir)
        self.assertEqual(len(exp.sources), 1)
        self.assertEqual(exp.sources[0].dir, self.plate_source_dir)
        self.assertEqual(exp.sources[0].name, self.plate_source_name)
        self.assertEqual(len(exp.sources[0].acquisitions), 1)
        self.assertEqual(exp.sources[0].acquisitions[0].dir,
                         self.acquisition_dir)
        self.assertEqual(exp.sources[0].acquisitions[0].index,
                         self.acquisition_index)

    def test_experiment_plates_attribute(self):
        exp = Experiment(self.experiment_dir)
        self.assertEqual(len(exp.plates), 1)
        self.assertEqual(exp.plates[0].dir, self.plate_dir)
        self.assertEqual(exp.plates[0].name, self.plate_name)
        self.assertEqual(len(exp.plates[0].cycles), 1)
        self.assertEqual(exp.plates[0].cycles[0].dir, self.cycle_dir)
        self.assertEqual(exp.plates[0].cycles[0].index, self.cycle_index)

    def test_experiment_adding_plate(self):
        exp = Experiment(self.experiment_dir)
        new_plate_name = 'newPlate'
        exp.add_plate(new_plate_name)
        self.assertEqual(len(exp.plates), 2)
        ix = [p.name for p in exp.plates].index(new_plate_name)
        self.assertEqual(exp.plates[ix].name, new_plate_name)
        self.assertEqual(len(exp.plates[ix].cycles), 0)


