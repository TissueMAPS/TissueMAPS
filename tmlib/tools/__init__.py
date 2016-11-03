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
A `tool` is an implementation of :class:`tmlib.tools.base.Tool`
that can process client requests and persist the result of the analysis
as an instance of :class:`tmlib.models.result.ToolResult` in the database.
The client can then stream the result in form of a
:class:`tmlib.models.layer.LabelLayer` or :class:`tmlib.models.plot.Plot`
to visualize it on the map in an interactive an responsive manner.

To create a new tool, one must implement :class:`tmlib.tools.base.Tool`,
decorate the derived class with :func:`tmlib.tools.registry.register_tool` and
import it in :mod:`tmlib.tools`.
'''
from tmlib.version import __version__
from tmlib.tools.classification import Classification
from tmlib.tools.clustering import Clustering
from tmlib.tools.heatmap import Heatmap
