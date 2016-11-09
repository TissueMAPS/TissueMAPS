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

Additional abstract bases classes are available for the *pandas* and *spark*
libraries: :class:`PandasInterface <tmlib.tools.base.PandasInterface>` and
:class:`SparkInterface <tmlib.models.base.SparkInterface>`). They serve as
`Mixins <https://en.wikipedia.org/wiki/Mixin>`_ and provide library-specific
methods for reading feature data from the database and writing tool results
back to the database. Methods common to both libraries can be provided on
the derived :class:`Tool <tmlib.tools.base.Tool>` class. However,
new functionality specific to either the *pandas* or *spark* library should be
implemented in a library-specific mixin class and provided to the tool class
via the ``__lib_bases__`` attribute. The class for the currently active library,
defined via the :attr:`tool_library <tmlib.config.LibraryConfig.tool_library>`
configuration parameter, will get automatically addded to the bases of the tool
class.

Consider the following example for a new tool named ``Foo``.
It requires an additional method to do the magic. The magic is library-specific
and is thus implemented in two separate mixin classes, namely ``FooPandas`` and
``FooSpark``. The implementation of the required ``do_magic`` method
for both libraries can be enforced by using an abstract base class, here called
``FooInterface``. The ``Foo`` class implements the abstract method
:meth:`process_request <tmlib.tools.base.Tool.process_request>`:

.. code-block:: python

    from abc import ABCMeta
    from abc import abstractmethod
    from tmlib.tools.base import Tool


    class FooInterface(object):

        __metaclass__ = ABCMeta

        @abstractmethod
        def do_magic(self, values):
            pass


    class FooPandas(FooInterface):

        def do_magic(self, values):
            # Do pandas magic here


    class FooSpark(FooInterface):

        def do_magic(self, values):
            # Do spark magic here


    class Foo(Tool):

        __icon__ = 'FOO'

        __description__ = 'Does some magic.'

        __lib_bases__ = {'pandas': FooPandas, 'spark': FooSpark}

        def __init__(self, experiment_id):
            super(Foo, self).__init__(experiment_id)

        def process_request(self, submission_id, payload):
            mapobject_type_name = payload['chosen_object_type']
            feature_name = payload['selected_feature']

            feature_values = self.load_feature_values(
                mapobject_type_name, feature_name
            )
            magic_labels = self.do_magic(feature_values)

            result_id = self.initialize_result(
                submission_id, mapobject_type_name,
                label_type='ContinuousLabelLayer'
            )

            self.save_label_values(result_id, magic_labels)


The actual magic is done by a meta class, acting behind the scenes to
dynamically adding the lib-specific mixin to the bases of ``Foo`` and
registering ``Foo`` to make available for use in the UI.


Note
----
Each tool also requires a client-side representation.
'''
from tmlib.version import __version__
from tmlib.tools.classification import Classification
from tmlib.tools.clustering import Clustering
from tmlib.tools.heatmap import Heatmap

from tmlib.tools.base import _register


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
    try:
        return _register[name]
    except KeyError:
        raise RegistryError('Tool "%s" is not registered.' % name)


def get_available_tools():
    '''Gets a list of available tools.

    Returns
    -------
    List[str]
        names of available tools
    '''
    return _register.keys()
