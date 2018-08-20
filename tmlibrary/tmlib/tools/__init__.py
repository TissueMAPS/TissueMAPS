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
'''Data analysis tools.

This packages provides tools for interactive data analysis and machine learning.
A *tool* is an implementation of :class:`Tool <tmlib.tools.base.Tool>`
that can process client requests and persist the result of the analysis
in form of an instance of :class:`ToolResult <tmlib.models.result.ToolResult>`
in the database. The client can stream the result provided via
:class:`LabelLayer <tmlib.models.layer.LabelLayer>` and
:class:`Plot <tmlib.models.plot.Plot>` and visualize it on the map in an
interactive an responsive manner.

Custom tools can be added by implementing :class:`Tool <tmlib.tools.base.Tool>`
and import the derived class in :mod:`tmlib.tools`.

Consider the following example for a new tool named ``Foo``.
It implements the abstract method
:meth:`process_request <tmlib.tools.base.Tool.process_request>` and an
additional method ``bar`` (which does nothing):

.. code-block:: python

    from tmlib.tools.base import Tool


    class Foo(Tool):

        __icon__ = 'FOO'

        __description__ = 'Does nothing.'

        def __init__(self, experiment_id):
            super(Foo, self).__init__(experiment_id)

        def bar(self, values):
            return values

        def process_request(self, submission_id, payload):
            mapobject_type_name = payload['chosen_object_type']
            feature_name = payload['selected_feature']

            values = self.load_feature_values(mapobject_type_name, [feature_name])
            labels = self.bar(values)

            result_id = self.register_result(
                submission_id, mapobject_type_name,
                label_type='ContinuousLabelLayer'
            )

            self.save_result_values(result_id, labels)


.. note:: Each tool also requires a client-side representation.
'''
import logging

from tmlib.version import __version__
from tmlib.tools.classification import Classification
from tmlib.tools.clustering import Clustering
from tmlib.tools.heatmap import Heatmap
from tmlib.tools.base import _register

logger = logging.getLogger(__name__)


def get_tool_class(name):
    '''Gets the tool-specific implementation of
    :class:`Tool <tmlib.models.base.Tool>`.

    Parameters
    ----------
    name: str
        name of the tool

    Returns
    -------
    type
        tool class
    '''
    logger.debug('get tool class "%s"', name)
    try:
        return _register[name]
    except KeyError:
        raise RegistryError('Tool "%s" is not registered.' % name)


def get_available_tools():
    '''Lists available tools.

    Returns
    -------
    List[str]
        names of available tools
    '''
    logger.debug('get available tools')
    return _register.keys()
