'''`TissueMAPS` database models.'''

from tmlib.models.base import Model, DateMixIn, File

import logging
import inspect
import collections
from sqlalchemy import create_engine
from sqlalchemy.sql.schema import Table
from sqlalchemy.sql.schema import UniqueConstraint
from sqlalchemy.sql.schema import PrimaryKeyConstraint

from tmlib.models.utils import Session

_postgresxl_register = collections.defaultdict(dict)

logger = logging.getLogger(__name__)


def distribute_by_hash(column_name):
    '''Registers a database model class for use with
    `PostgresXL <http://www.postgres-xl.org/>`_.

    Parameters
    ----------
    column_name: str
        name of the column that should be used as distribution hash

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
        _postgresxl_register['hash'][cls.__tablename__] = column_name
        return cls
    return decorator


# http://files.postgres-xl.org/documentation/ddl-constraints.html
# - In Postgres-XL, in distributed tables, UNIQUE constraints must include the distribution column of the table.
# - Please note that column with REFERENCES should be the distribution column. In this case, we cannot add PRIMARY KEY to order_id because PRIMARY KEY must be the distribution column as well.

# http://files.postgres-xl.org/documentation/sql-createtable.html
# - In Postgres-XL, if DISTRIBUTE BY REPLICATION is not specified, only the distribution key is allowed to have this constraint.
# - In Postgres-XL, if DISTRIBUTE BY REPLICATION is not specified, the distribution key must be included in the set of primary key columns.

def distribute_by_replication(cls):
    '''Registers a database model class for use with
    `PostgresXL <http://www.postgres-xl.org/>`_.

    Raises
    ------
    TypeError
        when decorated class is not derived from
        :py:class:`tmlib.models.Model`
    '''
    if Model not in inspect.getmro(cls):
        raise TypeError(
            'Registered class must be derived from tmlib.models.Model'
        )
    _postgresxl_register['replication'][cls.__tablename__] = True
    return cls


class PostgresXl(object):

    '''Destribution of SQL tables declared via SQLAlchemy for use with
    PostgresXL database cluster.
    '''

    def __init__(self, db_uri):
        '''
        Parameters
        ----------
        db_uri: str, optional
            URI of the database; defaults to
            :py:attribute:`tmlib.models.utils.DATABASE_URI`
        '''
        # TODO: this approach is quite a hack, this should be implemented in
        # SQLAlchemy at some point (see http://docs.sqlalchemy.org/en/latest/core/ddl.html)
        if db_uri is None:
            from tmlib.models.utils import DATABASE_URI
            db_uri = DATABASE_URI
        self._engine = create_engine(
            db_uri, strategy='mock', executor=self._dump
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
        print sql
        with Session() as session:
            session._engine.execute(sql)

    def _dump(self, sql, *multiparams, **params):
        if isinstance(sql, basestring):
            self._sql += sql + ';'
            return
        table_name = sql.element.name
        logger.info('create sql statement for table "%s"', table_name)
        create_table = str(sql.compile(dialect=self._engine.dialect)).rstrip()
        column_name = _postgresxl_register['hash'].get(table_name, None)
        if column_name is not None and isinstance(sql.element, Table):
            logger.info('distribute table "%s" by hash', table_name)
            primary_keys = [pk.name for pk in sql.element.primary_key]
            # The distributed column must be part of the UNIQUE and
            # PRIMARY KEY constraints
            for c in sql.element.constraints:
                # if isinstance(c, UniqueContraint):
                #     if column_name not in c.columns:
                #         sql.element.columns[column_name].unique = True
                # if isinstance(c, PrimaryKeyContraint):
                #     if column_name not in c.columns:
                #         sql.element.columns[column_name].primary_key = True
                if (isinstance(c, PrimaryKeyConstraint) or
                        isinstance(c, UniqueConstraint)):
                    if column_name not in c.columns:
                        c.columns.add(sql.element.columns[column_name])
            # The distributed column must be part of any INDEX
            for i in sql.element.indexes:
                if column_name not in i.columns:
                    i.columns.add(sql.element.columns[column_name])
            create_table += ' DISTRIBUTE BY HASH(' + column_name + ')'
        do_replicate = _postgresxl_register['hash'].get(table_name, False)
        if do_replicate and isinstance(sql.element, Table):
            logger.info('distribute table "%s" by replication', table_name)
            create_table += ' DISTRIBUTE BY REPLICATION'
        self._sql += create_table + ';' + '\n'


from tmlib.models.user import User
from tmlib.models.experiment import Experiment
from tmlib.models.well import Well
from tmlib.models.channel import Channel
from tmlib.models.layer import ChannelLayer
from tmlib.models.mapobject import MapobjectType, Mapobject, MapobjectSegmentation
from tmlib.models.feature import Feature, FeatureValue
from tmlib.models.plate import Plate
from tmlib.models.acquisition import Acquisition, ImageFileMapping
from tmlib.models.cycle import Cycle
from tmlib.models.submission import Submission, Task
from tmlib.models.site import Site
from tmlib.models.alignment import SiteShift, SiteIntersection
from tmlib.models.file import (
    MicroscopeImageFile, MicroscopeMetadataFile, ChannelImageFile,
    IllumstatsFile, PyramidTileFile
)


