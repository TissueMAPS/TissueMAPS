# TmLibrary - TissueMAPS library for distibuted image analysis routines.
# Copyright (C) 2016-2018 University of Zurich.
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
import collections


VERSION = '0.0.1'

Output = collections.namedtuple('Output', ['output_image'])


def main(input_image):

    assert input_image.dtype == np.uint16, 'image has wrong data type'

    assert input_image.shape == (10, 10, 3), 'image has wrong dimensions'

    assert input_image[2, 3, 0] == 69, 'image pixel has wrong value'

    return Output(input_image)
