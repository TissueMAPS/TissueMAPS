# TmLibrary - TissueMAPS library for distibuted image analysis routines.
# Copyright (C) 2016  Markus D. Herrmann, University of Zurich and Robin Hafen
# Copyright (C) 2018  University of Zurich
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
import os
import shutil
import random
import logging
import inspect
import collections
from copy import copy
from threading import Thread
from itertools import chain

import pandas as pd
import sqlalchemy
import sqlalchemy.orm
import sqlalchemy.pool
import sqlalchemy.exc
from sqlalchemy.engine.url import make_url
from sqlalchemy_utils.functions import quote
from sqlalchemy.event import listens_for
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from psycopg2.extras import NamedTupleCursor
from cached_property import cached_property

from tmlib.models.base import (
    MainModel, ExperimentModel, FileSystemModel, DistributedExperimentModel
)
from tmlib.models.dialect import *
from tmlib.utils import create_partitions
from tmlib import cfg

logger = logging.getLogger(__name__)

#: Dict[str, sqlalchemy.engine.base.Engine]: mapping of chached database
#: engine objects for reuse within the current Python process hashable by URL
DATABASE_ENGINES = {}

#: int: number of pooled database connections
POOL_SIZE = 5

_SCHEMA_NAME_FORMAT_STRING = 'experiment_{experiment_id}'


def set_pool_size(n):
    '''Sets the pool size for database connections of the current Python
    process.
    '''
    logger.debug('set size of database pool to %d', n)
    global POOL_SIZE
    POOL_SIZE = n


def create_db_engine(db_uri, cache=True):
    '''Creates a database engine with a given pool size.

    Parameters
    ----------
    db_uri: str
        database uri
    cache: bool, optional
        whether engine should be cached for reuse (default: ``True``)

    Returns
    -------
    sqlalchemy.engine.base.Engine
        created database engine

    '''
    if db_uri not in DATABASE_ENGINES:
        logger.debug(
            'create database engine for process %d with pool size %d',
            os.getpid(), POOL_SIZE
        )
        if POOL_SIZE > 1:
            overflow_size = POOL_SIZE * 2
        elif POOL_SIZE == 1:
            # For parallel processes running on the cluster, we want as few
            # database connections as possible. In principle one connection
            # should be enough.
            # However, we may want to have a "Session" and a "Connection"
            # each having a connection open, simulatenously. Therefore, we
            # allow an overflow of one additional connection.
            overflow_size = 1
        else:
            raise ValueError('Pool size must be a positive integer.')
        engine = sqlalchemy.create_engine(
            db_uri, poolclass=sqlalchemy.pool.QueuePool,
            pool_size=POOL_SIZE, max_overflow=overflow_size
        )
        if cache:
            logger.debug('cache database engine for reuse')
            DATABASE_ENGINES[db_uri] = engine
    else:
        logger.debug('reuse cached database engine for process %d', os.getpid())
        engine = DATABASE_ENGINES[db_uri]
    return engine


def create_db_tables(engine):
    '''Creates all tables in the *public* schema.

    Parameters
    ----------
    engine: sqlalchemy.engine

    '''
    logger.debug(
        'create tables of models derived from %s in schema "public"',
        MainModel.__name__
    )
    MainModel.metadata.create_all(engine)


def _assert_db_exists(engine):
    db_url = make_url(engine.url)
    db_name = db_url.database
    try:
        logger.debug('try to connect to database "%s": %s', db_name, db_url)
        connection = engine.connect()
        connection.close()
    except sqlalchemy.exc.OperationalError as err:
        db_url = make_url(engine.url)
        db_name = db_url.database
        logger.error('could not connect to database "%s": %s', db_name, str(err))
        raise ValueError('Cannot connect to database "%s".' % db_name)


def _set_search_path(connection, schema_name):
    if schema_name is not None:
        logger.debug('set search path to schema "%s"', schema_name)
        cursor = connection.connection.cursor()
        cursor.execute('''
            SET search_path TO 'public', %(schema)s;
        ''', {
            'schema': schema_name
        })
        cursor.close()


def _create_schema_if_not_exists(connection, schema_name):
    cursor = connection.connection.cursor()
    cursor.execute('''
        SELECT EXISTS(SELECT 1 FROM pg_namespace WHERE nspname = %(schema)s);
    ''', {
        'schema': schema_name
    })
    schema = cursor.fetchone()
    if schema[0]:
        cursor.close()
        return True
    else:
        logger.debug('create schema "%s"', schema_name)
        sql = 'CREATE SCHEMA IF NOT EXISTS %s;' % schema_name
        cursor.execute(sql)
        cursor.close()
        return False


def _drop_schema(connection, schema_name):
    logger.debug('drop all table in schema "%s"', schema_name)
    # NOTE: The tables are dropped on the worker nodes, but the schemas
    # persist. This is not a problem, however.
    cursor = connection.connection.cursor()
    cursor.execute('DROP SCHEMA IF EXISTS %s CASCADE;' % schema_name)
    cursor.close()


def _create_main_db_tables(connection):
    logger.debug(
        'create tables of models derived from %s for schema "public"',
        MainModel.__name__
    )
    MainModel.metadata.create_all(connection)


def _create_experiment_db_tables(connection, schema_name):
    logger.debug(
        'create tables of models derived from %s for schema "%s"',
        ExperimentModel.__name__, schema_name
    )
    # NOTE: We need to set the schema on copies of the tables otherwise
    # this messes up queries in a multi-tenancy use case.
    experiment_specific_metadata = sqlalchemy.MetaData(schema=schema_name)
    for name, table in ExperimentModel.metadata.tables.iteritems():
        table_copy = table.tometadata(experiment_specific_metadata)
    experiment_specific_metadata.create_all(connection)


# def _create_distributed_experiment_db_tables(connection, schema_name):
#     logger.debug(
#         'create distributed tables of models derived from %s for schema "%s"',
#         ExperimentModel.__name__, schema_name
#     )
#     experiment_specific_metadata = sqlalchemy.MetaData(schema=schema_name)
#     for name, table in ExperimentModel.metadata.tables.iteritems():
#         if table.info['is_distributed']:
#             table_copy = table.tometadata(experiment_specific_metadata)
#     experiment_specific_metadata.create_all(connection)


def create_db_session_factory():
    '''Creates a factory for creating a scoped database session that will use
    :class:`Query <tmlib.models.utils.Query>` to query the database.

    Returns
    -------
    sqlalchemy.orm.session.Session
    '''
    return sqlalchemy.orm.scoped_session(
        sqlalchemy.orm.sessionmaker(query_cls=Query)
    )


def delete_location(path):
    '''Deletes a location on disk.

    Parameters
    ----------
    path: str
        absolute path to directory or file
    '''
    if os.path.exists(path):
        logger.debug('remove location: %s', path)
        if os.path.isdir(path):
            shutil.rmtree(path)
        elif os.path.isfile(path):
            os.remove(path)


def remove_location_upon_delete(cls):
    '''Decorator function for an database model class that
    automatically removes the `location` that represents an instance of the
    class on the filesystem once the corresponding row is deleted from the
    database table.

    Parameters
    ----------
    cls: tmlib.models.base.DeclarativeABCMeta
       implemenation of :class:`tmlib.models.base.FileSystemModel`

    Raises
    ------
    AttributeError
        when decorated class doesn't have a "location" attribute
    '''
    def after_delete_callback(mapper, connection, target):
        delete_location(target.location)

    sqlalchemy.event.listen(cls, 'after_delete', after_delete_callback)
    return cls


def exec_func_after_insert(func):
    '''Decorator function for a database model class that calls the
    decorated function after an `insert` event.

    Parameters
    ----------
    func: function

    Examples
    --------
    @exec_func_after_insert(lambda target: do_something())
    SomeClass(db.Model):

    '''
    def class_decorator(cls):
        def after_insert_callback(mapper, connection, target):
            func(mapper, connection, target)
        sqlalchemy.event.listen(cls, 'after_insert', after_insert_callback)
        return cls
    return class_decorator


class Query(sqlalchemy.orm.query.Query):

    '''A custom query class.'''

    def __init__(self, *args, **kwargs):
        super(Query, self).__init__(*args, **kwargs)

    def delete(self):
        '''Performs a bulk delete query.

        Returns
        -------
        int
            count of rows matched as returned by the database's "row count"
            feature

        Note
        ----
        Also removes locations of instances on the file system.
        '''
        classes = [d['type'] for d in self.column_descriptions]
        locations = list()
        for cls in classes:
            if cls.__table__.info['is_distributed']:
                # TODO: check if in transaction
                logger.debug(
                    'delete records of distributed table "%s"',
                    cls.__table__.name
                )
            if hasattr(cls, '_location'):
                locations.extend(self.from_self(cls._location).all())
            elif hasattr(cls, 'location'):
                instances = self.from_self(cls).all()
                locations.extend([(inst.location,) for inst in instances])
            if cls.__name__ == 'Experiment':
                raise ValueError(
                    'To delete an experiment delete the corresponding '
                    'reference object.'
                )
            elif cls.__name__ == 'ExperimentReference':
                experiments = self.from_self(cls.id).all()
                connection = self.session.get_bind()
                for exp in experiments:
                    logger.info('drop schema of experiment %d', exp.id)
                    schema = _SCHEMA_NAME_FORMAT_STRING.format(
                        experiment_id=exp.id
                    )
                    _drop_schema(connection, schema)
        # For performance reasons delete all rows via raw SQL without updating
        # the session and then enforce the session to update afterwards.
        logger.debug(
            'delete instances of model class %s from database', cls.__name__
        )
        super(Query, self).delete(synchronize_session=False)
        self.session.expire_all()
        if locations:
            logger.debug('remove corresponding locations on disk')
            for loc in locations:
                if loc[0] is not None:
                    delete_location(loc[0])


class _SQLAlchemy_Session(object):

    '''A wrapper around an instance of an *SQLAlchemy* session
    that manages persistence of database model objects.

    An instance of this class will be exposed via
    :class:`MainSession <tmlib.models.utils.MainSession>` or
    :class:`ExperimentSession <tmlib.models.utils.ExperimentSession>`.

    Examples
    --------
    >>> import tmlib.models as tm
    >>> with tm.utils.MainSession() as session:
    >>>     print(session.drop_table(tm.Submission))

    '''

    def __init__(self, session, schema=None):
        '''
        Parameters
        ----------
        session: sqlalchemy.orm.session.Session
            *SQLAlchemy* database session
        schema: str, optional
            name of a database schema
        '''
        self._session = session
        self._schema = schema

    def __getattr__(self, attr):
        if hasattr(self._session, attr):
            return getattr(self._session, attr)
        elif hasattr(self, attr):
            return getattr(self, attr)
        else:
            raise AttributeError(
                'Object "%s" doens\'t have attribute "%s".'
                % (self.__class__.__name__, attr)
            )

    @property
    def connection(self):
        '''database connection'''
        return self._session.get_bind()

    def get_or_create(self, model, **kwargs):
        '''Gets an instance of a model class if it already exists or
        creates it otherwise.

        Parameters
        ----------
        model: type
            an implementation of :class:`tmlib.models.base.MainModel` or
            :class:`tmlib.models.base.ExperimentModel`
        **kwargs: dict
            keyword arguments for the instance that can be passed to the
            constructor of `model` or to
            :meth:`sqlalchemy.orm.query.query.filter_by`

        Returns
        -------
        tmlib.models.model
            an instance of `model`

        Note
        ----
        Adds and commits created instance. The approach can be useful when
        different processes may try to insert an instance constructed with the
        same arguments, but only one instance should be inserted and the other
        processes should re-use the instance without creation a duplication.
        The approach relies on uniqueness constraints of the corresponding table
        to decide whether a new entry would be considred a duplication.
        '''
        try:
            instance = self._session.query(model).\
                filter_by(**kwargs).\
                one()
            logger.debug('found existing instance: %r', instance)
        except sqlalchemy.orm.exc.NoResultFound:
            # We have to protect against situations when several worker
            # nodes are trying to insert the same row simultaneously.
            try:
                instance = model(**kwargs)
                self._session.add(instance)
                if not self._session.autocommit:
                    self._session.commit()
                else:
                    self._session.flush()
                logger.debug('created new instance: %r', instance)
            except sqlalchemy.exc.IntegrityError as err:
                logger.error(
                    'creation of %s instance failed:\n%s', model, str(err)
                )
                if not self._session.autocommit:
                    self._session.rollback()
                try:
                    instance = self._session.query(model).\
                        filter_by(**kwargs).\
                        one()
                    logger.debug('found existing instance: %r', instance)
                except:
                    raise
            except TypeError:
                raise TypeError(
                    'Wrong arugments for instantiation of model class "%s".'
                    % model.__name__
                )
            except:
                raise
        except:
            raise
        return instance

    def drop_table(self, model):
        '''Drops a database table for the given `model`. It also removes
        locations on disk in case `model` is derived from
        :class:`FileSytemModel <tmlib.models.base.FilesystemModel>`.

        Parameters
        ----------
        model: tmlib.models.MainModel or tmlib.models.ExperimentModel
            database model class

        Warning
        -------
        Disk locations are removed after the table is dropped. This can lead
        to inconsistencies between database and file system representation of
        `model` instances when the process is interrupted.
        '''
        connection = self._session.get_bind()
        locations_to_remove = []
        # We need to update the schema on each data model, such that tables
        # will be created for the correct experiment-specific schema and not
        # created for the "public" schema.
        experiment_specific_metadata = sqlalchemy.MetaData(schema=self._schema)
        for name, table in ExperimentModel.metadata.tables.iteritems():
            table_copy = table.tometadata(experiment_specific_metadata)
        # FIXME: quote
        table_name = '{schema}.{table}'.format(
            schema=self._schema, table=model.__table__.name
        )
        table = experiment_specific_metadata.tables[table_name]

        if table.exists(connection):
            if issubclass(model, FileSystemModel):
                model_instances = self._session.query(model).all()
                locations_to_remove = [m.location for m in model_instances]
            logger.info('drop table "%s"', table.name)
            self._session.commit()  # circumvent locking
            table.drop(connection)

        logger.info('remove "%s" locations on disk', model.__name__)
        for loc in locations_to_remove:
            logger.debug('remove "%s"', loc)
            delete_location(loc)

    def create_table(self, model):
        '''Creates a database table for the given `model`.

        Parameters
        ----------
        model: tmlib.models.MainModel or tmlib.models.ExperimentModel
            database model class
        '''
        connection = self._session.get_bind()
        # We need to update the schema on each data model, such that tables
        # will be created for the correct experiment-specific schema and not
        # created for the "public" schema.
        experiment_specific_metadata = sqlalchemy.MetaData(schema=self._schema)
        for name, table in ExperimentModel.metadata.tables.iteritems():
            table_copy = table.tometadata(experiment_specific_metadata)
        # FIXME: quote
        table_name = '{schema}.{table}'.format(
            schema=self._schema, table=model.__table__.name
        )
        table = experiment_specific_metadata.tables[table_name]
        logger.info('create table "%s"', table.name)
        table.create(connection)

    def bulk_ingest(self, instances):
        '''Ingests multiple instances of a distributed model class in bulk.

        Parameters
        ----------
        instances: List[tmlib.models.base.DistributedExperimentModel]
            instances of model class

        Warning
        -------
        Assumes that all instances are of the same model class.
        '''
        if len(instances) == 0:
            return
        inst = instances[0]
        cls = inst.__class__
        if not isinstance(inst, DistributedExperimentModel):
            raise TypeError(
                'Bulk ingestion is only supported for instances of type "%s"' %
                DistributedExperimentModel.__name__
            )
        connection = self._session.get_bind()
        with connection.connection.cursor() as c:
            cls._bulk_ingest(c, instances)

    def add(self, instance):
        '''Adds an instance of a model class.

        Parameters
        ----------
        instances: List[Union[tmlib.models.base.ExperimentModel, tmlib.models.base.MainModel]
            instance of a model class
        '''
        cls = instance.__class__
        if isinstance(instance, DistributedExperimentModel):
            connection = self._session.get_bind()
            with connection.connection.cursor() as c:
                cls._add(c, instance)
        else:
            self._session.add(instance)

    def add_all(self, instances):
        '''Adds multiple instances of a model class.

        Parameters
        ----------
        instances: List[Union[tmlib.models.base.ExperimentModel, tmlib.models.base.MainModel]
            instances of a the same model class

        Warning
        -------
        Assumes that all instances are of the same model class.
        '''
        if len(instances) == 0:
            return
        inst = instances[0]
        cls = inst.__class__
        if isinstance(inst, DistributedExperimentModel):
            connection = self._session.get_bind()
            with connection.connection.cursor() as c:
                for i in instances:
                    cls._add(c, i)
        else:
            self._session.add_all(instances)

class _Session(object):

    '''Class that provides access to all methods and attributes of
    :class:`sqlalchemy.orm.session.Session` and additional
    custom methods implemented in
    :class:`tmlib.models.utils._SQLAlchemy_Session`.

    Note
    ----
    The engine is cached and reused in case of a reconnection within the same
    Python process.

    Warning
    -------
    This is *not* thread-safe!
    '''

    def __init__(self, db_uri, schema=None, transaction=True):
        self._db_uri = db_uri
        self._schema = schema
        self._transaction = transaction
        self._session_factory = create_db_session_factory()

    def __exit__(self, except_type, except_value, except_trace):
        if self._transaction:
            if except_value:
                logger.debug(
                    'rolling back DB session %s due to error: %s',
                    self, except_value)
                self._session.rollback()
            else:
                try:
                    logger.debug('committing DB session %s ...', self)
                    self._session.commit()
                except RuntimeError as err:
                    logger.error('commit of DB session %s failed: %s', self, err)
        else:
            self._session.flush()
        connection = self._session.get_bind()
        connection.close()
        self._session.close()


class MainSession(_Session):

    '''Session scopes for interaction with the main ``tissuemaps`` database.
    All changes get automatically committed at the end of the interaction.
    In case of an error, a rollback is issued.

    Examples
    --------
    >>> import tmlib.models as tm
    >>> with tm.utils.MainSession() as session:
    >>>    print(session.query(tm.ExperimentReference).all())

    See also
    --------
    :class:`tmlib.models.base.MainModel`
    '''

    def __init__(self, transaction=True):
        '''
        Parameters
        ----------
        transaction: bool, optional
            whether a transaction should be used (default: ``True``)
        '''
        db_uri = cfg.db_master_uri
        super(MainSession, self).__init__(db_uri, transaction=transaction)
        self._schema = None
        self._engine = create_db_engine(db_uri)
        _assert_db_exists(self._engine)

    def __enter__(self):
        connection = self._engine.connect()
        self._session_factory.configure(bind=connection)
        self._session = _SQLAlchemy_Session(
            self._session_factory(), self._schema
        )
        return self._session


class ExperimentSession(_Session):

    '''Session scopes for interaction with an experiment-secific database.
    If ``transaction`` is set to ``True`` (default), all changes get
    automatically committed at the end of the interaction.
    In case of an error, a rollback is issued.
    If ``transaction`` is set to ``False``, the session will be in
    autocomit mode and every query will be immediately flushed to the database.

    Examples
    --------
    >>> import tmlib.models as tm
    >>> with tm.utils.ExperimentSession(experiment_id=1) as session:
    >>>     print(session.query(tm.Plate).all())

    Note
    ----
    Models derived from
    :class:`ExperimentModel <tmlib.models.base.ExperimentModel>` reside in a
    schema with name ``experiment_{id}``.
    The session will automatically set the *search_path*, such that one can
    refer to tables within the session scope without having to specifying the
    schema.

    See also
    --------
    :class:`tmlib.models.base.ExperimentModel`
    '''

    def __init__(self, experiment_id, transaction=True):
        '''
        Parameters
        ----------
        experiment_id: int
            ID of the experiment that should be queried
        transaction: bool, optional
            whether a transaction should be used; distributed tables cannot be
            modified within a transaction context (default: ``True``)
        '''
        db_uri = cfg.db_master_uri
        self.experiment_id = experiment_id
        logger.debug('create session for experiment %d', self.experiment_id)
        self._engine = create_db_engine(db_uri)
        schema = _SCHEMA_NAME_FORMAT_STRING.format(
            experiment_id=self.experiment_id
        )
        logger.debug('schema: "%s"', schema)
        super(ExperimentSession, self).__init__(db_uri, schema, transaction)

    def __enter__(self):
        connection = self._engine.connect()
        exists = _create_schema_if_not_exists(connection, self._schema)
        if not exists:
            _create_experiment_db_tables(connection, self._schema)
        if not self._transaction:
            connection = connection.execution_options(
                autocommit=True, isolation_level='AUTOCOMMIT'
            )
            # NOTE: SQLAlchemy docs say: "Executing queries outside of a
            # demarcated transaction is a legacy mode of usage, and can in
            # some cases lead to concurrent connection checkouts."
            self._session_factory.configure(
                autocommit=True, autoflush=False, expire_on_commit=False
            )
        _set_search_path(connection, self._schema)
        if not self._transaction:
            connection = connection.execution_options(
                autocommit=True, isolation_level='AUTOCOMMIT'
            )
            # NOTE: SQLAlchemy docs say: "Executing queries outside of a
            # demarcated transaction is a legacy mode of usage, and can in
            # some cases lead to concurrent connection checkouts."
            self._session_factory.configure(
                autocommit=True, autoflush=False, expire_on_commit=False
            )
        self._session_factory.configure(bind=connection)
        self._session = _SQLAlchemy_Session(
            self._session_factory(), self._schema
        )
        return self._session


class _Connection(object):

    '''A "raw" database connection which uses autocommit mode and is not
    part of a transaction.

    Such connections are required to issues statements such as
    ``CREATE DATABASE``, for example.

    Warning
    -------
    Only use a raw connection when absolutely required and when you know what
    you are doing.
    '''

    def __init__(self, db_uri, transaction):
        '''
        Parameters
        ----------
        db_uri: str
            URI of the database to connect to in the format required by
            *SQLAlchemy*
        '''
        self._db_uri = db_uri
        self._engine = create_db_engine(self._db_uri)
        self._transaction = transaction

    def __enter__(self):
        # NOTE: We need to run queries outside of a transaction in Postgres
        # autocommit mode.
        self._connection = self._engine.raw_connection()
        if not self._transaction:
            self._connection.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        _set_search_path(self._connection, self._schema)
        self._cursor = self._connection.cursor(cursor_factory=NamedTupleCursor)
        # NOTE: To achieve high throughput on UPDATE or DELETE, we
        # need to perform queries in parallel under the assumption that
        # order of records is not important (i.e. that they are commutative).
        # https://docs.citusdata.com/en/v6.0/performance/scaling_data_ingestion.html#real-time-updates-0-50k-s
        self._cursor.execute('''
            SET citus.shard_replication_factor = 1;
            SET citus.all_modifications_commutative TO on;
        ''')
        return self

    def __exit__(self, except_type, except_value, except_trace):
        if self._transaction:
            if except_value:
                logger.error('transaction rolled back due to error')
                self._connection.rollback()
            else:
                self._connection.commit()
        self._cursor.close()
        self._connection.close()

    def __getattr__(self, attr):
        if hasattr(self._cursor, attr):
            return getattr(self._cursor, attr)
        elif hasattr(self, attr):
            return getattr(self, attr)
        else:
            raise AttributeError(
                'Object "%s" doens\'t have attribute "%s".'
                % (self.__class__.__name__, attr)
            )


class ExperimentConnection(_Connection):

    '''Database connection for executing raw SQL statements for an
    experiment-specific database outside of a transaction context.

    Examples
    --------
    >>> import tmlib.models as tm
    >>> with tm.utils.ExperimentConnection(experiment_id=1) as connection:
    >>>     connection.execute('SELECT mapobject_id, value FROM feature_values')
    >>>     print(connection.fetchall())

    Warning
    -------
    Use raw connections only for modifying distributed tables. Otherwise use
    :class:`ExperimentSession <tmlib.models.utils.ExperimentSession>`.

    See also
    --------
    :class:`tmlib.models.base.ExperimentModel`
    '''

    def __init__(self, experiment_id, transaction=False):
        '''
        Parameters
        ----------
        experiment_id: int
            ID of the experiment that should be queried
        transaction: bool, optional
            whether a transaction should be began
        '''
        super(ExperimentConnection, self).__init__(
            cfg.db_master_uri, transaction
        )
        self._schema = _SCHEMA_NAME_FORMAT_STRING.format(
            experiment_id=experiment_id
        )
        self.experiment_id = experiment_id
        self._transaction = transaction

    def __enter__(self):
        # NOTE: We need to run queries outside of a transaction in Postgres
        # autocommit mode.
        self._connection = self._engine.raw_connection()
        if not self._transaction:
            self._connection.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        exists = _create_schema_if_not_exists(self._connection, self._schema)
        if not exists:
            _create_experiment_db_tables(self._connection, self._schema)
        _set_search_path(self._connection, self._schema)
        self._cursor = self._connection.cursor(cursor_factory=NamedTupleCursor)
        # NOTE: To achieve high throughput on UPDATE or DELETE, we
        # need to perform queries in parallel under the assumption that
        # order of records is not important (i.e. that they are commutative).
        # https://docs.citusdata.com/en/v6.0/performance/scaling_data_ingestion.html#real-time-updates-0-50k-s
        logger.debug('make modifications commutative')
        self._cursor.execute('''
            SET citus.shard_replication_factor = 1;
            SET citus.all_modifications_commutative TO on;
        ''')
        return self

    def locate_partition(self, model, partition_key):
        '''Determines the location of a table partition (shard).

        Parameters
        ----------
        model: class
            class derived from
            :class:`ExperimentModel <tmlib.models.base.ExperimentModel>`
        partition_key: int
            value of the distribution column

        Returns
        -------
        Tuple[Union[str, int]]
            host and port of the worker server and the ID of the shard
        '''
        self._cursor.execute('''
            SELECT get_shard_id_for_distribution_column(
                %(table)s, %(partition_key)s
            )
        ''', {
            'table': model.__table__.name,
            'partition_key': partition_key
        })
        record = self._cursor.fetchone()
        shard_id = record.get_shard_id_for_distribution_column
        self._cursor.execute('''
            SELECT nodename, nodeport FROM pg_dist_shard_placement
            WHERE shardid = %(shard_id)s
        ''', {
            'shard_id': shard_id
        })
        node, port = self._cursor.fetchone()
        return (node, port, shard_id)

    def get_unique_ids(self, model, n):
        '''Gets a unique, but shard-specific value for the distribution column.

        Parameters
        ----------
        model: class
            class derived from
            :class:`ExperimentModel <tmlib.models.base.ExperimentModel>`
        n: int
            number of IDs that should be returned

        Returns
        -------
        List[int]
            unique, shard-specific IDs

        Raises
        ------
        ValueError
            when the table of `model` is not distributed
        '''
        logger.debug(
            'get unique identifier for model "%s"', model.__name__
        )
        self._cursor.execute('''
            SELECT nextval(%(sequence)s) FROM generate_series(1, %(n)s);
        ''', {
            'sequence': '{t}_id_seq'.format(t=model.__table__.name),
            'n': n
        })
        values = self._cursor.fetchall()
        return [v[0] for v in values]

    def get_partition_placement(self, model_cls, partition_key):
        '''Finds the location of a partition of a distributed table.
        '''
        # utility function: get_shard_id_for_distribution_column()
        # metadata table: pg_dist_shard_placement
        pass


class MainConnection(_Connection):

    '''Database connection for executing raw SQL statements for the
    main ``tissuemaps`` database outside of a transaction context.

    Examples
    --------
    >>> import tmlib.models as tm
    >>> with tm.utils.MainConnection() as connection:
    >>>     connection.execute('SELECT name FROM plates')
    >>>     print(connection.fetchall())

    See also
    --------
    :class:`tmlib.models.base.MainModel`
    '''

    def __init__(self, transaction=False):
        '''
        Parameters
        ----------
        transaction: bool, optional
            whether a transaction should be began
        '''
        super(MainConnection, self).__init__(cfg.db_master_uri, transaction)


class ExperimentWorkerConnection(_Connection):

    '''Database connection for executing raw SQL statements on a database
    "worker" server to target individual shards of a distributed table.

    See also
    --------
    :class:`tmlib.models.base.ExperimentModel`
    '''

    def __init__(self, experiment_id, host, port, transaction=False):
        '''
        Parameters
        ----------
        experiment_id: int
            ID of the experiment that should be queried
        host: str
            IP address or name of database worker server
        port: str
            port to which database worker server listens
        transaction: bool, optional
            whether a transaction should be began
        '''
        db_uri = cfg.build_db_worker_uri(host, port)
        super(ExperimentWorkerConnection, self).__init__(db_uri, transaction)
        self._schema = _SCHEMA_NAME_FORMAT_STRING.format(
            experiment_id=experiment_id
        )
        self._host = host
        self._port = port
        self.experiment_id = experiment_id


def parallelize_query(func, args):
    '''Parallelize database query. This can be useful for targeting different
    shards of a distributed table. The number of parallel connections depends
    on the value of :attr:`POOL_SIZE <tmlib.models.utils.POOL_SIZE>`.

    Parameters
    ----------
    func: function
        a function that establishes a database connection and executes a given
        SQL query; function must return a list
    args: Union[list, generator]
        arguments that should be parsed to the function

    Returns
    -------
    list
        aggregated output of `function` return values

    Warning
    -------
    Don't use this function for distributed processing on the cluster, since
    this would establish too many simultaneous database connections.
    '''
    logger.debug('execute query in %d parallel threads', POOL_SIZE)
    n = len(args) / POOL_SIZE
    arg_batches = create_partitions(args, n)

    output = [None] * len(arg_batches)
    def wrapper(func, args, index):
        output[index] = func(args)

    threads = []
    for i, batch in enumerate(arg_batches):
        logger.debug('start thread #%d', i)
        # TODO: use queue or generator?
        t = Thread(target=wrapper, args=(func, batch, i))
        # TODO: use Event
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

    return list(chain(*output))
