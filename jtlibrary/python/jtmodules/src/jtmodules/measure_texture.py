# Copyright 2016 Markus D. Herrmann, University of Zurich
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
'''Jterator module for measuring texture features.'''
import collections
import jtlib.features


VERSION = '0.3.0'

Output = collections.namedtuple('Output', ['measurements', 'figure'])


def main(extract_objects, assign_objects, intensity_image, aggregate,
         frequencies=[1,5,10],
         measure_TAS=False,
         measure_LBP=False, radii=[1,5,10],
         measure_haralick=False, scales=[1,2],
         plot=False):
    '''Measures texture features for objects in `extract_objects` based
    on grayscale values in `intensity_image` and assign them to `assign_objects`.

    Parameters
    ----------
    extract_objects: numpy.ndarray[int32]
        label image with objects for which features should be extracted
    assign_objects: numpy.ndarray[int32]
        label image with objects to which extracted features should be assigned
    intensity_image: numpy.ndarray[unit8 or uint16]
        grayscale image from which features should be extracted
    aggregate: bool, optional
        whether measurements should be aggregated in case `extract_objects`
        and `assign_objects` have a many-to-one relationship
    frequencies: Set[int], optional
        frequencies of the Gabor filters (default: ``{1, 5, 10}``)
    measure_TAS: bool, optional
        whether *Threshold Adjacency Statistics (TAS)* features should
        be extracted
    measure_LBP: bool, optional
        whether *Local Binary Patterns (LBP)* should be extracted
    radii: Set[int], optional
        radii for defining pixel neighbourhood for Local Binary Patterns
        (LBP) (default: ``{1, 5, 10}``)
    scales: Set[int], optional
        scales at which to compute the Haralick textures
    measure_haralick: bool, optional
        whether *Haralick* features should be extracted
    plot: bool, optional
        whether a plot should be generated (default: ``False``)

    Returns
    -------
    jtmodules.measure_texture.Output[Union[List[pandas.DataFrame], str]]

    See also
    --------
    :class:`jtlib.features.Texture`
    '''
    f = jtlib.features.Texture(
        label_image=extract_objects,
        intensity_image=intensity_image,
        frequencies=frequencies,
        radius=radii,
        scales=scales,
        compute_haralick=measure_haralick,
        compute_TAS=measure_TAS,
        compute_LBP=measure_LBP
    )

    f.check_assignment(assign_objects, aggregate)

    if aggregate:
        measurements = [f.extract_aggregate(assign_objects)]
    else:
        measurements = [f.extract()]

    if plot:
        figure = f.plot()
    else:
        figure = str()

    return Output(measurements, figure)
