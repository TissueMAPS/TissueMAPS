#!/usr/bin/env python
import unittest
from tmlib.experiment import Experiment
from tmlib.testing.argparser import parser
from tmlib.testing import logo


class TestCycle(unittest.TestCase):

    def setUp(self):
        experiment_dir = '/Users/mdh/testdata/150820-Testset-CV'
        self.experiment = Experiment(experiment_dir)

    def assert_correct_image_metadata_assignment(self):
        for c in self.experiment.cycles:
            for i, f in enumerate(c.image_files):
                self.assertEqual(f, c.image_metadata[i],
                    'image filenames and corresponding metadata attribute '
                    'do not match')


if __name__ == '__main__':

    args = parser.parse_args()

    print logo

    unittest.main(verbosity=args.verbosity)
