import os
import shutil
import logging
import sqlalchemy
import sqlalchemy.orm
import sqlalchemy.pool
from tmlib.models import ExperimentModel
from sqlalchemy_utils.functions import database_exists
from sqlalchemy_utils.functions import create_database
from sqlalchemy_utils.functions import drop_database


logger = logging.getLogger(__name__)

#: URI for the TissueMAPS database
DATABASE_URI = os.environ['TMAPS_DB_URI']


def create_db_engine(db_uri=DATABASE_URI):
    '''Creates a database engine with a connection pool size of ``5``
    and maximal overflow of ``10``.

    Parameters
    ----------
    db_uri: str, optional
        database uri; defaults to value of environment variable `TMAPS_DB_URI`

    Returns
    -------
    sqlalchemy.engine.base.Engine
    '''
    # This creates a default Pool.
    # If this creates problems, consider using a different poolclass,
    # e.g. sqlalchemy.pool.AssertionPool and/or changing settings, such as
    # pool_size or max_overflow.
    return sqlalchemy.create_engine(
        db_uri, poolclass=sqlalchemy.pool.QueuePool,
        pool_size=5, max_overflow=10
    )


def create_db_session_factory(engine):
    '''Creates a factory for creating a scoped database session that will use
    :py:class:`tmlib.models.utils.Query` to query the database.

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

    Parameter
    ---------
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
    '''Decorator function for a database model class that automatically removes
    the location that represents an instance of the class on the filesystem
    once the corresponding row is deleted from the database table.

    Examples
    --------
    from tmlib.models import Model
    from tmlib.models.utils import remove_location_upon_delete

    @remove_location_upon_delete
    class SomeClassWithALocationOnDisk(Model):
        """A database model class"""

    '''
    def after_delete_callback(mapper, connection, target):
        delete_location(target.location)

    sqlalchemy.event.listen(cls, 'after_delete', after_delete_callback)
    return cls


def exec_func_after_insert(func):
    '''
    @exec_func_after_insert(lambda target: do_something())
    SomeClass(db.Model):
    ...

    '''
    def class_decorator(cls):
        def after_insert_callback(mapper, connection, target):
            func(mapper, connection, target)
        sqlalchemy.event.listen(cls, 'after_insert', after_insert_callback)
        return cls
    return class_decorator


class Query(sqlalchemy.orm.query.Query):

    '''A query class with custom methods.'''

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
        instances = self.all()
        locations = [getattr(inst, 'location', None) for inst in instances]
        # For performance reasons delete all rows via raw SQL without updating
        # the session and then enforce the session to update afterwards.
        if instances:
            logger.debug(
                'delete %d instances of class %s from database',
                len(instances), instances[0].__class__.__name__
            )
            super(Query, self).delete(synchronize_session=False)
            self.session.expire_all()
        if locations:
            logger.debug('remove corresponding locations on disk')
            for loc in locations:
                if loc is not None:
                    delete_location(loc)


class SQLAlchemy_Session(object):

    '''A wrapper around an instance of
    :py:class:`sqlalchemy.orm.session.Session` that manages persistence of
    database model objects.
    '''

    def __init__(self, session):
        '''
        Parameters
        ----------
        session: sqlalchemy.orm.session.Session
            `SQLAlchemy` database session
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
            an implementation of the :py:class:`tmlib.models.model`
            abstract base class
        **kwargs: dict
            keyword arguments for the instance that can be passed to the
            constructor of `model` or to
            :py:method:`sqlalchemy.orm.query.query.filter_by`

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
        '''Drops a database table and re-creates it.

        Parameters
        ----------
        model: tmlib.models.MainModel or tmlib.models.ExperimentModel
            database model class

        Note
        ----
        Performs a commit before dropping the table to circumvent locking.
        '''
        table = model.__table__
        engine = self._session.get_bind()
        self._session.commit()
        if table.exists(engine):
            logger.debug('drop table "%s"', table.name)
            table.drop(engine)
        logger.debug('create table "%s"', table.name)
        table.create(engine)

    def get_or_create_all(self, model, args):
        '''Gets a collection of instances of a model class if they already
        exist or create them otherwise.

        Parameters
        ----------
        model: type
            an implementation of the :py:class:`tmlib.models.ExperimentModel`
            or :py:class:`tmlib.models.MainModel` abstract base class
        args: List[dict]
            keyword arguments for each instance that can be passed to the
            constructor of `model` or to
            :py:method:`sqlalchemy.orm.query.Query.filter_by`

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

    '''
    It provide access to all methods and attributes of
    :py:class:`sqlalchemy.orm.session.Session` and additional
    custom methods implemented in
    :py:class:`tmlib.models.utils.SQLAlchemy_Session`.

    Note
    ----
    The engine is cached and reused in case of a reconnection within the same
    Python process.

    Warning
    -------
    This is *not* thread-safe!
    '''
    _engines = dict()
    _session_factories = dict()

    def __enter__(self):
        if self._db_uri not in self.__class__._session_factories:
            self.__class__._engines[self._db_uri] = \
                create_db_engine(self._db_uri)
            self.__class__._session_factories[self._db_uri] = \
                create_db_session_factory(self.__class__._engines[self._db_uri])
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
        '''Deletes locations defined by instances of :py:class`tmlib.Model`
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

    '''Session scopes for interaction with the main `TissueMAPS` database.

    Examples
    --------
    from tmlib.models.utils import Session
    from tmlib.models import Experiment

    with MainSession() as session:
        print session.query(Experiment).all()

    Note
    ----
    All changes get automatically committed at the end of the interaction.
    In case of an error, a rollback is issued.

    See also
    --------
    :py:class:`tmlib.models.MainModel`
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
            self._db_uri = DATABASE_URI
        else:
            self._db_uri = db_uri
        if not database_exists(self._db_uri):
            raise ValueError('Database does not exist: %s' % self._db_uri)


class ExperimentSession(_Session):

    '''Session scopes for interaction with an experiment-secific `TissueMAPS`
    database.

    Examples
    --------
    from tmlib.models.utils import Session
    from tmlib.models import Plate

    with ExperimentSession(experiment_id=1) as session:
        print session.query(Plate).all()

    Note
    ----
    All changes get automatically committed at the end of the interaction.
    In case of an error, a rollback is issued.

    See also
    --------
    :py:class:`tmlib.models.ExperimentModel`
    '''

    def __init__(self, experiment_id, db_uri=None):
        '''
        Parameters
        ----------
        experiment_id: int
            ID of the experiment that should be accessed
        db_uri: str, optional
            URI of the main `TissueMAPS` database; defaults to the value of
            the environment variable ``TMPAS_DB_URI`` (default: ``None``)
        '''
        if db_uri is None:
            db_uri = DATABASE_URI
        self.experiment_id = experiment_id
        if self.experiment_id is not None:
            if not isinstance(self.experiment_id, int):
                raise TypeError('Argument "experiment_id" must have type int.')
            self._db_uri = '{main}_experiment_{id}'.format(
                main=db_uri, id=self.experiment_id
            )

    def __enter__(self):
        if database_exists(self._db_uri):
            do_create_tables = False
        else:
            logger.debug(
                'create database for experiment %d', self.experiment_id
            )
            create_database(self._db_uri)
            do_create_tables = True
        if self._db_uri not in self.__class__._session_factories:
            self.__class__._engines[self._db_uri] = \
                create_db_engine(self._db_uri)
            self.__class__._session_factories[self._db_uri] = \
                sqlalchemy.orm.scoped_session(
                    sqlalchemy.orm.sessionmaker(
                        bind=self.__class__._engines[self._db_uri],
                        query_cls=Query
                    )
                )
            if do_create_tables:
                engine = self.__class__._engines[self._db_uri]
                # TODO: create template with postgis extension already created
                logger.debug(
                    'create postgis extension in database for experiment %d',
                    self.experiment_id
                )
                engine.execute('CREATE EXTENSION postgis;')
                logger.debug(
                    'create tables in database for experiment %d',
                    self.experiment_id
                )
                ExperimentModel.metadata.create_all(engine)
        session_factory = self.__class__._session_factories[self._db_uri]
        self._session = SQLAlchemy_Session(session_factory())
        return self._session

