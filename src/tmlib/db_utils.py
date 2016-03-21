import base64
import yaml
import simplecrypt
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def create_tmaps_database_engine():
    '''
    Create an engine for the `TissueMAPS` database.

    Returns
    -------
    sqlalchemy.engine.base.Engine
    '''
    url = 'postgresql://{user}:{password}@{host}:{port}/tissuemaps'.format(
        user='markus', password=123, host='localhost', port=5432
    )
    return create_engine(url)


class Session(object):

    '''
    Class for creating a session scope for interaction with the database.
    All changes get automatically committed at the end of the interaction.
    In case an error occurs, a rollback is issued.

    Examples
    --------
    >>>with Session() as session:
           session.query()
    '''

    def __enter__(self):
        engine = create_tmaps_database_engine()
        Session = sessionmaker(bind=engine)
        self.session = Session()
        return self.session

    def __exit__(self, except_type, except_value, except_trace):
        if except_value:
            self.session.rollback()
        else:
            self.session.commit()
        self.session.close()


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
