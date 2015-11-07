from hashids import Hashids
from flask import current_app


class DecodeFailedException(Exception):
    pass


SALT_ALPHABET = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890'


def decode(pk):
    hasher = Hashids(salt=current_app.config['HASHIDS_SALT'],
                     min_length=8)
    decoded_id = hasher.decode(pk)
    if not decoded_id:
        raise DecodeFailedException(
            'Was not able to decode the given string')
    else:
        return decoded_id[0]


def encode(pk):
    hasher = Hashids(salt=current_app.config['HASHIDS_SALT'],
                     min_length=8)
    return hasher.encode(pk)
