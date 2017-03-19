# TmLibrary - TissueMAPS library for distibuted image analysis routines.
# Copyright (C) 2016  Markus D. Herrmann, University of Zurich and Robin Hafen
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
import numpy as np


VERSION = '0.0.1'


def main(input_image_py, input_image_m, input_image_r):

    np.testing.assert_array_equal(
        input_image_1, input_image_2,
        err_msg='input images py and m are not equal'
    )

    np.testing.assert_array_equal(
        input_image_1, input_image_3,
        err_msg='input images py and r are not equal'
    )

