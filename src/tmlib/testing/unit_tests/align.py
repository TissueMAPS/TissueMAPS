import unittest
import numpy as np

from tmlib.workflow.align.registration import calculate_shift
from tmlib.workflow.align.registration import calculate_overhang
from tmlib.image_utils import shift_and_crop


class TestImageAlignment(unittest.TestCase):

    def setUp(self):
        dims = (100, 100)
        self.images = dict()
        self.images['ref'] = np.zeros(dims)
        self.images['ref'][45:55, 45:55] = 1
        self.images['ul'] = np.zeros(dims)
        self.images['ul'][10:20, 20:30] = 1
        self.images['up'] = np.zeros(dims)
        self.images['up'][10:20, 45:55] = 1
        self.images['ur'] = np.zeros(dims)
        self.images['ur'][10:20, 70:80] = 1
        self.images['ri'] = np.zeros(dims)
        self.images['ri'][45:55, 70:80] = 1
        self.images['lr'] = np.zeros(dims)
        self.images['lr'][80:90, 70:80] = 1
        self.images['lo'] = np.zeros(dims)
        self.images['lo'][80:90, 45:55] = 1
        self.images['ll'] = np.zeros(dims)
        self.images['ll'][80:90, 20:30] = 1
        self.images['le'] = np.zeros(dims)
        self.images['le'][45:55, 20:30] = 1
        self.y = dict()
        self.x = dict()
        for name, img in self.images.iteritems():
            self.y[name], self.x[name] = calculate_shift(img, self.images['ref'])
        up, lo, ri, le = calculate_overhang(self.y.values(), self.x.values())
        self.upper_overhang = up
        self.lower_overhang = lo
        self.right_overhang = ri
        self.left_overhang = le
        self.aligned_ref_img = shift_and_crop(
            self.images['ref'], self.y['ref'], self.x['ref'],
            self.lower_overhang, self.upper_overhang,
            self.right_overhang, self.left_overhang
        )

    def tearDown(self):
        pass

    def test_upper_overhangs(self):
        assert self.upper_overhang == 35

    def test_lower_overhang(self):
        assert self.lower_overhang == 35

    def test_left_overhang(self):
        assert self.left_overhang == 25

    def test_right_overhang(self):
        assert self.right_overhang == 25

    def test_no_shift(self):
        assert self.y['ref'] == 0
        assert self.x['ref'] == 0

    def test_upper_left_shift(self):
        print self.y['ul']
        print self.x['ul']
        assert self.y['ul'] == 35
        assert self.x['ul'] == 25

    def test_upper_left_alignment(self):
        aligned_ul_img = shift_and_crop(
            self.images['ul'], self.y['ul'], self.x['ul'],
            self.lower_overhang, self.upper_overhang,
            self.right_overhang, self.left_overhang
        )
        np.testing.assert_equal(aligned_ul_img, self.aligned_ref_img)

    def test_lower_right_shift(self):
        assert self.y['lr'] == -35
        assert self.x['lr'] == -25

    def test_lower_right_alignment(self):
        aligned_lr_img = shift_and_crop(
            self.images['lr'], self.y['lr'], self.x['lr'],
            self.lower_overhang, self.upper_overhang,
            self.right_overhang, self.left_overhang
        )
        np.testing.assert_equal(aligned_lr_img, self.aligned_ref_img)

    def test_upper_right_shift(self):
        assert self.y['ur'] == 35
        assert self.x['ur'] == -25

    def test_upper_right_alignment(self):
        aligned_ur_img = shift_and_crop(
            self.images['ur'], self.y['ur'], self.x['ur'],
            self.lower_overhang, self.upper_overhang,
            self.right_overhang, self.left_overhang
        )
        np.testing.assert_equal(aligned_ur_img, self.aligned_ref_img)

    def test_lower_left_shift(self):
        assert self.y['ll'] == -35
        assert self.x['ll'] == 25

    def test_lower_left_aligment(self):
        aligned_ll_img = shift_and_crop(
            self.images['ll'], self.y['ll'], self.x['ll'],
            self.lower_overhang, self.upper_overhang,
            self.right_overhang, self.left_overhang
        )
        np.testing.assert_equal(aligned_ll_img, self.aligned_ref_img)

    def test_lower_shift(self):
        assert self.y['lo'] == -35
        assert self.x['lo'] == 0

    def test_lower_aligment(self):
        aligned_lo_img = shift_and_crop(
            self.images['lo'], self.y['lo'], self.x['lo'],
            self.lower_overhang, self.upper_overhang,
            self.right_overhang, self.left_overhang
        )
        np.testing.assert_equal(aligned_lo_img, self.aligned_ref_img)

    def test_upper_shift(self):
        assert self.y['up'] == 35
        assert self.x['up'] == 0

    def test_upper_aligment(self):
        aligned_up_img = shift_and_crop(
            self.images['up'], self.y['up'], self.x['up'],
            self.lower_overhang, self.upper_overhang,
            self.right_overhang, self.left_overhang
        )
        np.testing.assert_equal(aligned_up_img, self.aligned_ref_img)

    def test_left_shift(self):
        assert self.y['le'] == 0
        assert self.x['le'] == 25

    def test_left_aligment(self):
        aligned_le_img = shift_and_crop(
            self.images['le'], self.y['le'], self.x['le'],
            self.lower_overhang, self.upper_overhang,
            self.right_overhang, self.left_overhang
        )
        np.testing.assert_equal(aligned_le_img, self.aligned_ref_img)

    def test_right_shift(self):
        assert self.y['ri'] == 0
        assert self.x['ri'] == -25

    def test_right_aligment(self):
        aligned_ri_img = shift_and_crop(
            self.images['ri'], self.y['ri'], self.x['ri'],
            self.lower_overhang, self.upper_overhang,
            self.right_overhang, self.left_overhang
        )
        np.testing.assert_equal(aligned_ri_img, self.aligned_ref_img)

