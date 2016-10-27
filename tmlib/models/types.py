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
    Uses the `lxml <http://lxml.de/>`_ packages for processing.
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
