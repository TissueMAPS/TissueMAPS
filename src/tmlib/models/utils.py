import os
import shutil
import logging
import base64
import yaml
import simplecrypt
import sqlalchemy
from sqlalchemy import event
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)

#: URI for the TissueMAPS database
DATABASE_URI = os.path.expandvars('$TMAPS_DB_URI')


def create_db_engine():
    '''
    Returns
    -------
    sqlalchemy.engine.base.Engine
    '''
    return sqlalchemy.create_engine(DATABASE_URI)


def auto_remove_directory(get_location_func):
    """
    @auto_remove_directory(lambda target: target.location)
    SomeClassWithADirectoryOnDisk(db.Model):
    ...

    """
    def class_decorator(cls):
        def after_delete_callback(mapper, connection, target):
            loc = get_location_func(target)
            if os.path.exists(loc):
                logger.info('remove location: %s', loc)
                shutil.rmtree(loc)

        sqlalchemy.event.listen(cls, 'after_delete', after_delete_callback)
        return cls
    return class_decorator


def auto_create_directory(get_location_func):
    """
    @auto_create_directory(lambda target: target.location)
    SomeClassWithADirectoryOnDisk(db.Model):
    ...

    """
    def class_decorator(cls):
        def after_insert_callback(mapper, connection, target):
            loc = get_location_func(target)
            if not os.path.exists(loc):
                logger.info('create location: %s', loc)
                os.mkdir(loc)
            else:
                logger.warn('location already exists: %s', loc)
        event.listen(cls, 'after_insert', after_insert_callback)
        return cls
    return class_decorator


def exec_func_after_insert(func):
    """
    @exec_func_after_insert(lambda target: do_something())
    SomeClass(db.Model):
    ...

    """
    def class_decorator(cls):
        def after_insert_callback(mapper, connection, target):
            func(mapper, connection, target)
        event.listen(cls, 'after_insert', after_insert_callback)
        return cls
    return class_decorator


class Session(object):

    '''
    Create a session scope for interaction with the database.
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
    
    Warining
    --------
    This is *not* thread-safe!
    '''
    _engine = None
    _session_factory = None

    def __enter__(self):
        if Session._engine is None:
            Session._engine = create_db_engine()
        if Session._session_factory is None:
            Session._session_factory = sqlalchemy.orm.sessionmaker(
                bind=self._engine
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

    def delete(self, *args, **kwargs):
        '''Delegates to :py:method:`sqlalchemy.orm.session.Session.delete`'''
        return self._sqla_session.delete(*args, **kwargs)

    def get_or_create(self, model, **kwargs):
        '''Get a particular instance of a model class if it already exists and
        create it otherwise.

        Parameters
        ----------
        model: type
            an implementation of the :py:class:`tmlib.models.Model`
            abstract base class
        kwargs: dict
            keyword arguments for the constructor of the model class

        Returns
        -------
        tmlib.models.Model
            an instance of `model`
        '''
        try:
            inst = self.query(model).filter_by(**kwargs).one()
            logger.debug('got existing instance: %r', inst)
        except sqlalchemy.orm.exc.NoResultFound:
            inst = model(**kwargs)
            self._sqla_session.add(inst)
            self._sqla_session.flush()
            logger.debug('created new instance: %r', inst)
        except sqlalchemy.exc.IntegrityError:
            self._sqla_session.rollback()
            inst = self.query(model).filter_by(**kwargs).one()
            logger.debug('got existing instance: %r', inst)
        except:
            raise
        return inst


def decode_pk(key):
    '''
    Decode public key.

    Parameters
    ----------
    key: str
        encoded public key

    Returns
    -------
    int
        decoded public key
    '''
    return int(base64.urlsafe_b64decode(str(key))[5:])


def encode_pk(string):
    '''
    Encode public key.

    Parameters
    ----------
    string: int
        public key

    Returns
    -------
    str
        encode public key
    '''
    return base64.urlsafe_b64encode('tmaps' + str(string))


def decrypt_pk(key, name):
    '''
    Decode key for access to experiments via the command line interface.

    Parameters
    ----------
    key: str
        encoded mapping
    name: str
        key name

    Returns
    -------
    dict
        decoded access information
    '''
    return yaml.safe_load(simplecrypt.decrypt(str(name), key))


def encrypt_pk(mapping, name):
    '''
    Encode mapping that provides access information to an experiment for use
    via the command line interface.

    Parameters
    ----------
    mapping: dict
        access information
    name: str
        key name

    Returns
    -------
    str
        encoded access information
    '''
    return simplecrypt.encrypt(str(name), yaml.safe_dump(mapping))

