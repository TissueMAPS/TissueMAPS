'''`TissueMAPS` database models.'''

from tmlib.models.base import Model, DateMixIn, File

import logging
import inspect
import collections
from sqlalchemy import create_engine
from sqlalchemy.sql.schema import Table

from tmlib.models.utils import DATABASE_URI
from tmlib.models.utils import Session

_postgresxl_register = collections.defaultdict(dict)

logger = logging.getLogger(__name__)


def distribute_by(column_name):
    '''Register a database model class for use with
    `PostgresXL <http://www.postgres-xl.org/>`_.

    Parameters
    ----------
    column_name: str
        name of the column that should be used for distribution of the table

    Raises
    ------
    TypeError
        when decorated class is not derived from
        :py:class:`tmlib.models.Model`
    '''
    def decorator(cls):
        if Model not in inspect.getmro(cls):
            raise TypeError(
                'Registered class must be derived from tmlib.models.Model'
            )
        _postgresxl_register[cls.__tablename__] = column_name
        return cls
    return decorator


class PostgresXl(object):

    '''Destribution of SQL tables declared via SQLAlchemy for use with
    PostgresXL database cluster.
    '''

    def __init__(self):
        # TODO: this approach is quite a hack, this should be implemented in
        # SQLAlchemy at some point (see http://docs.sqlalchemy.org/en/latest/core/ddl.html)
        self._engine = create_engine(
            DATABASE_URI, strategy='mock', executor=self._dump
        )
        self._sql = str()

    def generate_create_table_statements(self):
        '''Generates SQL `CREATE TABLE` statements for all model classes
        derived from :py:class:`tmlib.models.Model`.

        Returns
        -------
        str
            SQL statement
        '''
        Model.metadata.create_all(self._engine, checkfirst=False)
        return self._sql

    def create_tables(self):
        '''Creates all tables declared by model classes derived from
        :py:class:`tmlib.models.Model`.
        '''
        sql = self.generate_create_table_statements()
        with Session() as session:
            session._engine.execute(sql)

    def _dump(self, sql, *multiparams, **params):
        if isinstance(sql, basestring):
            self._sql += sql + ';'
            return
        table_name = sql.element.name
        logger.info('create sql statement for table "%s"', table_name)
        create_table = str(sql.compile(dialect=self._engine.dialect)).rstrip()
        column_name = _postgresxl_register.get(table_name, None)
        if column_name is not None and isinstance(sql.element, Table):
            logger.info('distribute table "%s"', table_name)
            create_table += ' DISTRIBUTE BY HASH(' + column_name + ')'
        self._sql += create_table + ';' + '\n'


from tmlib.models.user import User
from tmlib.models.experiment import Experiment
from tmlib.models.well import Well
from tmlib.models.channel import Channel
from tmlib.models.layer import ChannelLayer
from tmlib.models.mapobject import MapobjectType, Mapobject, MapobjectSegmentation, MapobjectType
from tmlib.models.feature import Feature, FeatureValue
from tmlib.models.plate import Plate
from tmlib.models.acquisition import Acquisition, ImageFileMapping
from tmlib.models.cycle import Cycle
from tmlib.models.submission import Submission, Task
from tmlib.models.site import Site
from tmlib.models.alignment import SiteShift, SiteIntersection
from tmlib.models.file import MicroscopeImageFile, MicroscopeMetadataFile, ChannelImageFile, ProbabilityImageFile, IllumstatsFile, PyramidTileFile


