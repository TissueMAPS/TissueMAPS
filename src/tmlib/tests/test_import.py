import unittest


class TestPackageImports(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_import_tmlib(self):
        try:
            import tmlib
        except ImportError:
            raise AssertionError('tmlib cannot be imported')

    def test_import_vips(self):
        try:
            from gi.repository import Vips
        except ImportError:
            raise AssertionError('Vips cannot be imported')
