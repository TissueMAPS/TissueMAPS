import os
import shutil
import logging
import sqlalchemy
import sqlalchemy.orm

logger = logging.getLogger(__name__)

#: URI for the TissueMAPS database
DATABASE_URI = os.environ['TMAPS_DB_URI']


def create_db_engine():
    '''Creates a database engine.

    Returns
    -------
    sqlalchemy.engine.base.Engine
    '''
    return sqlalchemy.create_engine(DATABASE_URI)


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
        loc = target.location
        if os.path.exists(loc):
            logger.debug('remove location: %s', loc)
            if os.path.isdir(loc):
                shutil.rmtree(loc)
            elif os.path.isfile(loc):
                os.remove(loc)

    sqlalchemy.event.listen(cls, 'after_delete', after_delete_callback)
    # sqlalchemy.event.listen(
    #     Session, 'after_bulk_delete', after_delete_callback
    # )
    return cls


# def auto_create_directory(get_location_func):
#     """
#     @auto_create_directory(lambda target: target.location)
#     SomeClassWithADirectoryOnDisk(db.Model):
#     ...

#     """
#     def class_decorator(cls):
#         def after_insert_callback(mapper, connection, target):
#             loc = get_location_func(target)
#             if not os.path.exists(loc):
#                 logger.info('create location: %s', loc)
#                 os.mkdir(loc)
#             else:
#                 logger.warn('location already exists: %s', loc)
#         sqlalchemy.event.listen(cls, 'after_insert', after_insert_callback)
#         return cls
#     return class_decorator


def exec_func_after_insert(func):
    """
    @exec_func_after_insert(lambda target: do_something())
    SomeClass(db.Model):
    ...

    """
    def class_decorator(cls):
        def after_insert_callback(mapper, connection, target):
            func(mapper, connection, target)
        sqlalchemy.event.listen(cls, 'after_insert', after_insert_callback)
        return cls
    return class_decorator


class Session(object):

    '''Create a session scope for interaction with the database.
    All changes get automatically committed at the end of the interaction.
    In case an error occurs, a rollback is issued.

    Examples
    --------
    >>>with Session() as session:
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
                sqlalchemy.orm.sessionmaker(bind=self._engine)
            )
        self._sqla_session = Session._session_factory()
        return self

    def __exit__(self, except_type, except_value, except_trace):
        if except_value:
            self._sqla_session.rollback()
        else:
            self._sqla_session.commit()
        self._sqla_session.close()

    def query(self, *args, **kwargs):
        '''Delegates to :py:method:`sqlalchemy.orm.session.Session.query`'''
        return self._sqla_session.query(*args, **kwargs)

    def get(self, *args, **kwargs):
        '''Delegates to :py:method:`sqlalchemy.orm.session.Session.get`'''
        return self._sqla_session.get(*args, **kwargs)

    def add(self, *args, **kwargs):
        '''Delegates to :py:method:`sqlalchemy.orm.session.Session.add`'''
        return self._sqla_session.add(*args, **kwargs)

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

    def get_or_create(self, model, **kwargs):
        '''Get an instance of a model class if it already exists or
        create it otherwise.

        Parameters
        ----------
        model: type
            an implementation of the :py:class:`tmlib.models.Model`
            abstract base class
        **kwargs: dict
            keyword arguments for the constructor of the model class

        Returns
        -------
        tmlib.models.Model
            an instance of `model`
        '''
        try:
            instance = self.query(model).filter_by(**kwargs).one()
            logger.debug('found existing instance: %r', instance)
        except sqlalchemy.orm.exc.NoResultFound:
            # We have to protect against situations when several worker
            # nodes are trying to insert the same row simultaneously.
            try:
                instance = model(**kwargs)
                self._sqla_session.add(instance)
                self._sqla_session.commit()
                logger.debug('created new instance: %r', instance)
            except sqlalchemy.exc.IntegrityError:
                self._sqla_session.rollback()
                instance = self.query(model).filter_by(**kwargs).one()
                logger.debug('found existing instance: %r', instance)
            except:
                raise
        except:
            raise
        return instance

    def get_or_create_all(self, model, args):
        '''Get a collection of instances of a model class if they already exist
        or create them otherwise.

        Parameters
        ----------
        model: type
            an implementation of the :py:class:`tmlib.models.Model`
            abstract base class
        args: List[dict]
            keyword arguments for the constructor of the model class

        Returns
        -------
        List[tmlib.models.Model]
            instances of `model`
        '''
        collection = list()
        for kwargs in args:
            collection.extend(
                self.query(model).filter_by(**kwargs).all()
            )
        if not collection:
            try:
                collection = list()
                for kwargs in args:
                    collection.append(model(**kwargs))
                self._sqla_session.add_all(collection)
                self._sqla_session.commit()
            except sqlalchemy.exc.IntegrityError:
                self._sqla_session.rollback()
                collection = list()
                for kwargs in args:
                    collection.extend(
                        self.query(model).filter_by(**kwargs).all()
                    )
            except:
                raise
        return collection
