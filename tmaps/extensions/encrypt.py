from hashids import Hashids
from flask import current_app


SALT_ALPHABET = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890'


def decode(pk):
    hasher = Hashids(salt=current_app.config['HASHIDS_SALT'],
                     min_length=8)
    return hasher.decode(pk)[0]


def encode(pk):
    hasher = Hashids(salt=current_app.config['HASHIDS_SALT'],
                     min_length=8)
    return hasher.encode(pk)
