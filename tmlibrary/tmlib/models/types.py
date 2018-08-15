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
'''Custom SQLalchemy data types.
'''
from lxml import etree
from sqlalchemy.types import TypeDecorator, UnicodeText
from geoalchemy2 import Geometry
from geoalchemy2.functions import GenericFunction


class XML(TypeDecorator):

    '''XML data column type.

    Note
    ----
    Uses the `lxml <http://lxml.de/>`_ package for processing.
    '''

    impl = UnicodeText
    type = etree._Element

    def get_col_spec(self):
        return 'XML'

    def bind_processor(self, dialect):
        def process(value):
            if value is not None:
                return etree.tostring(value, encoding='UTF-8')
            else:
                return None
        return process

    def process_result_value(self, value, dialect):
        if value is not None:
            value = etree.fromstring(value)
        return value


class ST_Expand(GenericFunction):

    '''Implementation of the Postgis function
    `ST_Expand <http://postgis.net/docs/ST_Expand.html>`_.
    '''

    name = 'ST_Expand'
    type = Geometry


class ST_ExteriorRing(GenericFunction):

    '''Implementation of the Postgis function
    `ST_ExteriorRing <http://postgis.net/docs/ST_ExteriorRing.html>`_.
    '''

    name = 'ST_ExteriorRing'
    type = Geometry


class ST_Boundary(GenericFunction):

    '''Implementation of the Postgis function
    `ST_Boundary <http://postgis.net/docs/ST_Boundary.html>`_.
    '''

    name = 'ST_Boundary'
    type = Geometry


class ST_IsValid(GenericFunction):

    '''Implementation of the Postgis function
    `ST_IsValid <http://postgis.net/docs/ST_IsValid.html>`_.
    '''

    name = 'ST_IsValid'
    type = Geometry


class ST_GeomFromText(GenericFunction):

    '''Implementation of the Postgis function
    `ST_GeomFromText <http://postgis.net/docs/ST_GeomFromText.html>`_.
    '''

    name = 'ST_GeomFromText'
    type = Geometry


class ST_SimplifyPreserveTopology(GenericFunction):

    '''Implementation of the Postgis function
    `ST_SimplifyPreserveTopology <http://postgis.net/docs/ST_SimplifyPreserveTopology.html>`_.
    '''

    name = 'ST_SimplifyPreserveTopology'
    type = Geometry
