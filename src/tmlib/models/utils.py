import os
import shutil
import logging
import sqlalchemy
import sqlalchemy.orm
import sqlalchemy.pool

logger = logging.getLogger(__name__)

#: URI for the TissueMAPS database
DATABASE_URI = os.environ['TMAPS_DB_URI']


def create_db_engine():
    '''Creates a database engine with a connection pool size of ``2``.

    Returns
    -------
    sqlalchemy.engine.base.Engine
    '''
    # This creates a default Pool.
    # If this creates problems, consider using a different poolclass,
    # e.g. sqlalchemy.pool.AssertionPool and/or changing settings, such as
    # pool_size or max_overflow.
    return sqlalchemy.create_engine(
        DATABASE_URI,
        poolclass=sqlalchemy.pool.QueuePool, pool_size=5, max_overflow=10
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


class Session(object):

    '''A session scope for interaction with the database.
    All changes get automatically committed at the end of the interaction.
    In case of an error, a rollback is issued.

    Examples
    --------
    from tmlib.models.utils import Session

    with Session() as session:
        session.query()

    Note
    ----
    The engine is cached and reused in case of a reconnection within the same
    Python process.

    Warning
    -------
    This is *not* thread-safe!
    '''
    _engine = None
    _session_factory = None

    def __enter__(self):
        if Session._engine is None:
            Session._engine = create_db_engine()
        if Session._session_factory is None:
            Session._session_factory = sqlalchemy.orm.scoped_session(
                sqlalchemy.orm.sessionmaker(
                    bind=Session._engine, query_cls=Query
                )
            )
        self._sqla_session = Session._session_factory()
        return self

    def __exit__(self, except_type, except_value, except_trace):
        if except_value:
            self._sqla_session.rollback()
        else:
            sqlalchemy.event.listen(
                self._session_factory, 'after_bulk_delete',
                self._after_bulk_delete_callback
            )
            self._sqla_session.commit()
        self._sqla_session.close()

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

    def query(self, *args, **kwargs):
        '''Delegates to :py:method:`sqlalchemy.orm.session.Session.query`'''
        return self._sqla_session.query(*args, **kwargs)

    def get(self, *args, **kwargs):
        '''Delegates to :py:method:`sqlalchemy.orm.session.Session.get`'''
        return self._sqla_session.get(*args, **kwargs)

    def add(self, *args, **kwargs):
        '''Delegates to :py:method:`sqlalchemy.orm.session.Session.add`'''
        return self._sqla_session.add(*args, **kwargs)

    def bulk_save_objects(self, *args, **kwargs):
        '''Delegates to :py:method:`sqlalchemy.orm.session.Session.bulk_save_objects`'''
        return self._sqla_session.bulk_save_objects(*args, **kwargs)

    def bulk_insert_mappings(self, *args, **kwargs):
        '''Delegates to :py:method:`sqlalchemy.orm.session.Session.bulk_insert_mappings`'''
        return self._sqla_session.bulk_insert_mappings(*args, **kwargs)

    def bulk_update_mappings(self, *args, **kwargs):
        '''Delegates to :py:method:`sqlalchemy.orm.session.Session.bulk_update_mappings`'''
        return self._sqla_session.bulk_update_mappings(*args, **kwargs)

    def add_all(self, *args, **kwargs):
        '''Delegates to :py:method:`sqlalchemy.orm.session.Session.add_all`'''
        return self._sqla_session.add_all(*args, **kwargs)

    def flush(self, *args, **kwargs):
        '''Delegates to :py:method:`sqlalchemy.orm.session.Session.flush`'''
        return self._sqla_session.flush(*args, **kwargs)

    def commit(self, *args, **kwargs):
        '''Delegates to :py:method:`sqlalchemy.orm.session.Session.commit`'''
        return self._sqla_session.commit(*args, **kwargs)

    def rollback(self, *args, **kwargs):
        '''Delegates to :py:method:`sqlalchemy.orm.session.Session.rollback`'''
        return self._sqla_session.rollback(*args, **kwargs)

    def delete(self, *args, **kwargs):
        '''Delegates to :py:method:`sqlalchemy.orm.session.Session.delete`'''
        return self._sqla_session.delete(*args, **kwargs)

    def scalar(self, *args, **kwargs):
        '''Delegates to :py:method:`sqlalchemy.orm.session.Session.scalar`'''
        return self._sqla_session.scalar(*args, **kwargs)

    def update_or_create(self, model, **kwargs):
        '''Updates an instance of a model class if it already exists or
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
        Adds and pushes newly created instance.

        Warning
        -------
        No commit is performed. The approach may not protect against concurrent
        parallel insertions.
        '''
        try:
            instance = self.query(model).filter_by(**kwargs).one()
            logger.debug('found existing instance: %r', instance)
            logger.debug(
                'update existings instance with parameters: {0}'.format(kwargs)
            )
            for k, v in kwargs.iteritems():
                setattr(instance, k, v)
        except sqlalchemy.orm.exc.NoResultFound:
            instance = model(**kwargs)
            logger.debug('created new instance: %r', instance)
            self._sqla_session.add(instance)
            self._sqla_session.push()
        except:
            raise
        return instance

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
                self._sqla_session.add(instance)
                self._sqla_session.commit()
                logger.debug('added and committed new instance: %r', instance)
            except sqlalchemy.exc.IntegrityError as err:
                logger.error(
                    'creation of instance %r failed:\n%s', instance, str(err)
                )
                self._sqla_session.rollback()
                instance = self.query(model).filter_by(**kwargs).one()
                logger.debug('found existing instance: %r', instance)
            except:
                raise
        except:
            raise
        return instance

    def get_or_create_all(self, model, args):
        '''Gets a collection of instances of a model class if they already
        exist or create them otherwise.

        Parameters
        ----------
        model: type
            an implementation of the :py:class:`tmlib.models.Model`
            abstract base class
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
                self._sqla_session.add_all(instances)
                self._sqla_session.commit()
            except sqlalchemy.exc.IntegrityError:
                self._sqla_session.rollback()
                instances = list()
                for kwargs in args:
                    instances.extend(
                        self.query(model).filter_by(**kwargs).all()
                    )
            except:
                raise
        return instances

