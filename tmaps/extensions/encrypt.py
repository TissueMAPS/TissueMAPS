from hashids import Hashids
from flask import current_app
from sqlalchemy import event


SALT_ALPHABET = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890'


def decode(pk):
    hasher = Hashids(salt=current_app.config['HASHIDS_SALT'],
                     min_length=8)
    return hasher.decode(pk)[0]


def encode(pk):
    hasher = Hashids(salt=current_app.config['HASHIDS_SALT'],
                     min_length=8)
    return hasher.encode(pk)


def auto_generate_hash(cls):
    """
    Class decorator to add an 'after_insert' event listener.
    Whenever an instance of the class is created and added to the database,
    the 'id' attribute is hashed and saved in the 'hash' attribute (String).
    Make sure that the decorated class actually has a hash attribute. E.g.:

    @auto_generate_hash
    SomeClassWhoseIdShouldBeHashed(db.Model):
        ...
        id = db.Column(db.Integer, primary_key=True)
        hash = db.Column(db.String(20))
        ...

    """
    def after_insert_callback(mapper, connection, target):
        tbl = mapper.local_table
        connection.execute(
            tbl.update().\
                values(hash=encode(target.id)).\
                where(tbl.c.id == target.id)
        )
    event.listen(cls, 'after_insert', after_insert_callback)
    return cls
