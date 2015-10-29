import unittest


class TestPackageImports(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_vips_import(self):
        try:
            from gi.repository import Vips
        except ImportError:
            raise AssertionError('Vips cannot be imported')
