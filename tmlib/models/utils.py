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
import os
import shutil
import random
import logging
import inspect
import sqlalchemy
import sqlalchemy.orm
import sqlalchemy.pool
import sqlalchemy.exc
from sqlalchemy.engine.url import make_url
from sqlalchemy_utils.functions import create_database
from sqlalchemy_utils.functions import drop_database
from sqlalchemy_utils.functions import quote
from sqlalchemy.event import listens_for
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from psycopg2.extras import DictCursor

from tmlib.models.base import ExperimentModel, FileSystemModel
from tmlib import cfg

logger = logging.getLogger(__name__)

#: Dict[str, sqlalchemy.engine.base.Engine]: mapping of chached database
#: engine objects for reuse within the current Python process hashable by URL
DATABASE_ENGINES = {}


def create_db_engine(db_uri, cache=True, pool_size=5):
    '''Creates a database engine with a given pool size.

    Parameters
    ----------
    db_uri: str
        database uri
    cache: bool, optional
        whether engine should be cached for reuse (default: ``True``)
    pool_size: int, optional
        number of pooled database connections (default: ``5``)

    Returns
    -------
    sqlalchemy.engine.base.Engine
        created database engine

    '''
    if db_uri not in DATABASE_ENGINES:
        logger.debug('create database engine for process %d', os.getpid())
        engine = sqlalchemy.create_engine(
            db_uri, poolclass=sqlalchemy.pool.QueuePool,
            pool_size=pool_size, max_overflow=pool_size*2,
            # SQLAlchemy (or actually psycopg2) makes use of multi-statement
            # transactions using BEGIN and COMMIT/ROLLBACK. The BEGIN is
            # automatically issued. This may cause problems when sharding
            # tables with Citus, for example. We may want to  turn it off to
            # use the Postgres default mode:
            # https://gist.github.com/carljm/57bfb8616f11bceaf865
        )
        if cache:
            logger.debug('cache database engine for reuse')
            DATABASE_ENGINES[db_uri] = engine
    else:
        logger.debug('reuse cached database engine for process %d', os.getpid())
    return DATABASE_ENGINES[db_uri]


def _try_to_connect_to_db(engine):
    try:
        connection = engine.connect()
        connection.close()
    except sqlalchemy.exc.OperationalError:
        db_url = make_url(engine.url)
        db_name = db_url.database
        raise ValueError('Cannot connect to database "%s".' % db_name)


def _create_db_if_not_exists(engine, create_tables=True):
    try:
        connection = engine.connect()
        connection.close()
    except sqlalchemy.exc.OperationalError:
        db_url = make_url(engine.url)
        db_url.database = 'template1'
        db_name = db_url.database
        logger.debug('create database %s', db_name)
        with _Connection(db_url) as conn:
            conn.execute('CREATE DATABASE {name}'.format(
                name=quote(engine, db_name))
            )
            if engine.name == 'citus':
                logger.debug('create citus extension for database %s', db_name)
                conn.execute('CREATE EXTENSION citus;')
            logger.debug('create postgis extension for database %s', db_name)
            conn.execute('CREATE EXTENSION postgis;')
            logger.debug('create tables for database %s', db_name)

        if create_tables:
            if db_name == 'tissuemaps':
                logger.debug(
                    'create tables of models derived from %s',
                    MainModel.__name__
                )
                MainModel.metadata.create_all(engine)
            else:
                logger.debug(
                    'create tables of models derived from %s',
                    ExperimentModel.__name__
                )
                ExperimentModel.metadata.create_all(engine)
                logger.debug(
                    'set storage type of "pixels" column of '
                    '"channel_layer_tiles" table to MAIN'
                )
                conn.execute(
                    'ALTER TABLE channel_layer_tiles ALTER COLUMN pixels SET STORAGE MAIN;'
                )


# @listens_for(sqlalchemy.pool.Pool, 'connect')
# def _on_pool_connect(dbapi_con, connection_record):
#     logger.debug('create database connection: %d', dbapi_con.get_backend_pid())


# @listens_for(sqlalchemy.pool.Pool, 'checkin')
# def _on_pool_checkin(dbapi_con, connection_record):
#     logger.debug(
#         'database connection returned to pool: %d',
#         dbapi_con.get_backend_pid()
#     )


# @listens_for(sqlalchemy.pool.Pool, 'checkout')
# def _on_pool_checkout(dbapi_con, connection_record, connection_proxy):
#     logger.debug(
#         'database connection retrieved from pool: %d',
#         dbapi_con.get_backend_pid()
#     )


def create_db_session_factory(engine):
    '''Creates a factory for creating a scoped database session that will use
    :class:`Query <tmlib.models.utils.Query>` to query the database.

    Parameters
    ----------
    engine: sqlalchemy.engine.base.Engine

    Returns
    -------
    sqlalchemy.orm.session.Session
    '''
    return sqlalchemy.orm.scoped_session(
        sqlalchemy.orm.sessionmaker(bind=engine, query_cls=Query)
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

    if not hasattr(cls, 'location'):
        raise AttributeError(
            'Decorated class must have a "location" attribute'
        )
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
                for exp in experiments:
                    logger.debug('drop database of experiment %d', exp.id)
                    db_uri = cfg.get_db_uri_sqla(experiment_id=exp.id)
                    engine = create_db_engine(db_uri)
                    _drop_db_if_exists(engine)
                    for host in cfg.db_worker_hosts:
                        url = cfg.get_db_uri_sqla(
                            experiment_id=experiment_id, host=host
                        )
                        engine = create_db_engine(db_uri, cache=False)
                        _drop_db_if_exists(engine)
        # For performance reasons delete all rows via raw SQL without updating
        # the session and then enforce the session to update afterwards.
        logger.debug(
            'delete instances of class %s from database', cls.__name__
        )
        super(Query, self).delete(synchronize_session=False)
        self.session.expire_all()
        if locations:
            logger.debug('remove corresponding locations on disk')
            for loc in locations:
                if loc[0] is not None:
                    delete_location(loc[0])


class SQLAlchemy_Session(object):

    '''A wrapper around an instance of an *SQLAlchemy* session
    that manages persistence of database model objects.
    '''

    def __init__(self, session):
        '''
        Parameters
        ----------
        session: sqlalchemy.orm.session.Session
            *SQLAlchemy* database session
        '''
        self._session = session

    def __getattr__(self, attr):
        if hasattr(self._session, attr):
            return getattr(self._session, attr)
        elif hasattr(self, attr):
            return getattr(self, attr)
        else:
            raise AttributeError(
                'Object "%s" doens\'t have an attribute "%s".'
                % (self.__class__.__name__, attr)
            )

    @property
    def engine(self):
        '''sqlalchemy.engine.Engine: engine for the database connection'''
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
            instance = self.query(model).filter_by(**kwargs).one()
            logger.debug('found existing instance: %r', instance)
        except sqlalchemy.orm.exc.NoResultFound:
            # We have to protect against situations when several worker
            # nodes are trying to insert the same row simultaneously.
            try:
                instance = model(**kwargs)
                logger.debug('created new instance: %r', instance)
                self._session.add(instance)
                self._session.commit()
                logger.debug('added and committed new instance: %r', instance)
            except sqlalchemy.exc.IntegrityError as err:
                logger.error(
                    'creation of instance %r failed:\n%s', instance, str(err)
                )
                self._session.rollback()
                try:
                    instance = self.query(model).filter_by(**kwargs).one()
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

    def drop_and_recreate(self, model):
        '''Drops a database table and re-creates it. Also removes
        locations on disk for each row of the dropped table.

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
        table = model.__table__
        engine = self._session.get_bind()
        locations_to_remove = []
        if table.exists(engine):
            if issubclass(model, FileSystemModel):
                model_instances = self._session.query(model).all()
                locations_to_remove = [m.location for m in model_instances]
            logger.info('drop table "%s"', table.name)
            self._session.commit()  # circumvent locking
            table.drop(engine)
        logger.info('create table "%s"', table.name)
        table.create(engine)
        logger.info('remove "%s" locations on disk', model.__name__)
        for loc in locations_to_remove:
            logger.debug('remove "%s"', loc)
            delete_location(loc)

    def get_or_create_all(self, model, args):
        '''Gets a collection of instances of a model class if they already
        exist or create them otherwise.

        Parameters
        ----------
        model: type
            an implementation of the :class:`tmlib.models.ExperimentModel`
            or :class:`tmlib.models.base.MainModel` abstract base class
        args: List[dict]
            keyword arguments for each instance that can be passed to the
            constructor of `model` or to
            ::meth:`sqlalchemy.orm.query.Query.filter_by`

        Returns
        -------
        List[tmlib.models.Model]
            instances of `model`
        '''
        instances = list()
        for kwargs in args:
            instances.extend(
                self.query(model).filter_by(**kwargs).all()
            )
        if not instances:
            try:
                instances = list()
                for kwargs in args:
                    instances.append(model(**kwargs))
                self._session.add_all(instances)
                self._session.commit()
            except sqlalchemy.exc.IntegrityError:
                self._session.rollback()
                instances = list()
                for kwargs in args:
                    instances.extend(
                        self.query(model).filter_by(**kwargs).all()
                    )
            except:
                raise
        return instances


class _Session(object):

    '''Class that provides access to all methods and attributes of
    :class:`sqlalchemy.orm.session.Session` and additional
    custom methods implemented in
    :class:`tmlib.models.utils.SQLAlchemy_Session`.

    Note
    ----
    The engine is cached and reused in case of a reconnection within the same
    Python process.

    Warning
    -------
    This is *not* thread-safe!
    '''
    _session_factories = dict()

    def __init__(self, db_uri):
        self._db_uri = db_uri
        if self._db_uri not in self.__class__._session_factories:
            self.__class__._session_factories[self._db_uri] = \
                create_db_session_factory(self.engine)

    @property
    def engine(self):
        '''sqlalchemy.engine: engine object for the currently used database'''
        return create_db_engine(self._db_uri)

    def __enter__(self):
        session_factory = self.__class__._session_factories[self._db_uri]
        self._session = SQLAlchemy_Session(session_factory())
        return self._session

    def __exit__(self, except_type, except_value, except_trace):
        if except_value:
            self._session.rollback()
        else:
            # TODO: if experiment is deleted, also delete its database
            self._session.commit()
            sqlalchemy.event.listen(
                self._session_factories[self._db_uri],
                'after_bulk_delete', self._after_bulk_delete_callback
            )
        self._session.close()

    def _after_bulk_delete_callback(self, delete_context):
        '''Deletes locations defined by instances of :class`tmlib.Model`
        after they have been deleted en bulk.

        Parameters
        ----------
        delete_context: sqlalchemy.orm.persistence.BulkDelete
        '''
        logger.debug(
            'deleted %d rows from table "%s"',
            delete_context.rowcount, delete_context.primary_table.name
        )


class MainSession(_Session):

    '''Session scopes for interaction with the main ``tissuemaps`` database.
    All changes get automatically committed at the end of the interaction.
    In case of an error, a rollback is issued.

    Examples
    --------
    >>> import tmlib.models as tm

    >>> with tm.utils.MainSession() as session:
    >>>    print session.query(tm.ExperimentReference).all()

    See also
    --------
    :class:`tmlib.models.base.MainModel`
    '''

    def __init__(self, db_uri=None):
        '''
        Parameters
        ----------
        db_uri: str, optional
            URI of the main `TissueMAPS` database; defaults to the value of
            the environment variable ``TMPAS_DB_URI`` (default: ``None``)
        '''
        if db_uri is None:
            db_uri = cfg.get_db_uri_sqla()
        super(MainSession, self).__init__(db_uri)
        engine = create_db_engine(db_uri)
        _try_to_connect_to_db(engine)


class ExperimentSession(_Session):

    '''Session scopes for interaction with an experiment-secific database.
    All changes get automatically committed at the end of the interaction.
    In case of an error, a rollback is issued.

    Examples
    --------
    >>> import tmlib.models as tm

    >>> with tm.utils.ExperimentSession(experiment_id=1) as session:
    >>>     print session.query(tm.Plate).all()

    See also
    --------
    :class:`tmlib.models.base.ExperimentModel`
    '''

    def __init__(self, experiment_id, db_uri=None):
        '''
        Parameters
        ----------
        experiment_id: int
            ID of the experiment that should be queried
        db_uri: str, optional
            URI of the main ``tissuemaps`` database; defaults to the value
            returned by
            :meth:`get_db_uri_sqla <tmlib.config.LibraryConfig.get_db_uri_sqla>`
        '''
        if db_uri is None:
            db_uri = cfg.get_db_uri_sqla(experiment_id=experiment_id)
        self.experiment_id = experiment_id
        engine = create_db_engine(db_uri)
        _create_db_if_not_exists(engine)
        for host in cfg.db_worker_hosts:
            url = cfg.get_db_uri_sqla(experiment_id=experiment_id, host=host)
            engine = create_db_engine(db_uri, cache=False, pool_size=1)
            _create_db_if_not_exists(engine, create_tables=False)
        super(ExperimentSession, self).__init__(db_uri)

    def __enter__(self):
        session_factory = self.__class__._session_factories[self._db_uri]
        self._session = SQLAlchemy_Session(session_factory())
        return self._session


class _Connection(object):

    def __init__(self, db_uri):
        self._db_uri = db_uri
        create_db_engine(self._db_uri)

    def __enter__(self):
        self._connection = DATABASE_ENGINES[self._db_uri].raw_connection()
        self._connection.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        self._cursor = self._connection.cursor(cursor_factory=DictCursor)
        return self._cursor

    def __exit__(self, except_type, except_value, except_trace):
        self._connection.close()


class ExperimentConnection(_Connection):

    '''Database connection for executing raw SQL statements for an
    experiment-specific database outside of a transaction context.

    Examples
    --------
    >>> import tmlib.models as tm

    >>> with tm.utils.ExperimentConnection(experiment_id=1) as connection:
    >>>     connection.execute('SELECT mapobject_id, value FROM feature_values;')
    >>>     print connection.fetchall()

    Warning
    -------
    Use raw connections only if absolutely necessary, otherwise use
    :class:`ExperimentSession <tmlib.models.utils.ExperimentSession>`.

    See also
    --------
    :class:`ExperimentModel <tmlib.models.base.ExperimentModel>`
    '''

    def __init__(self, experiment_id, db_uri=None):
        '''
        Parameters
        ----------
        experiment_id: int
            ID of the experiment that should be queried
        db_uri: str, optional
            database URI; defaults to the value returned by
            :meth:`get_db_uri_sqla <tmlib.config.DefaultConfig.get_db_uri_sqla>`
            given the provided `experiment_id`
        '''
        if db_uri is None:
            db_uri = cfg.get_db_uri_sqla(experiment_id=experiment_id)
        engine = create_db_engine(db_uri)
        _create_db_if_not_exists(engine)
        super(ExperimentConnection, self).__init__(db_uri)
        self.experiment_id = experiment_id


class MainConnection(_Connection):

    '''Database connection for executing raw SQL statements for the
    main ``tissuemaps`` database outside of a transaction context.

    Examples
    --------
    >>> import tmlib.models as tm

    >>> with tm.utils.MainConnection() as connection:
    >>>     connection.execute('SELECT name FROM plates;')
    >>>     connection.fetchall()

    Warning
    -------
    Use raw connnections only if absolutely necessary, otherwise use
    :class:`MainSession <tmlib.models.utils.MainSession>`.

    See also
    --------
    :class:`MainModel <tmlib.models.base.MainModel>`
    '''

    def __init__(self, db_uri=None):
        '''
        Parameters
        ----------
        db_uri: str, optional
            database URI; defaults to the value returned by
            :meth:`get_db_uri_sqla <tmlib.config.DefaultConfig.get_db_uri_sqla>`
        '''
        if db_uri is None:
            db_uri = cfg.get_db_uri_sqla()
        engine = create_db_engine(db_uri)
        _try_to_connect_to_db(engine)
        super(MainConnection, self).__init__(db_uri)
