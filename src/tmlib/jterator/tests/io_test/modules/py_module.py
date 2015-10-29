# encoding: utf-8
import numpy as np


def py_module(InputImage1, InputImage2, InputImage3, **kwargs):

    np.testing.assert_array_equal(InputImage1, InputImage2,
        err_msg=('Outputs of "%s" and "%s" are not equal'
                 % ('myInitialPythonModule.py', 'myMatlabModule.m')))

    np.testing.assert_array_equal(InputImage1, InputImage3,
        err_msg=('Outputs of "%s" and "%s" are not equal'
                 % ('myInitialPythonModule.py', 'myRModule.m')))

    print '\n🍺  TEST PASSED! Outputs are identical!'
