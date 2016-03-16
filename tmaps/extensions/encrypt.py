from hashids import Hashids
import base64
from flask import current_app


class DecodeFailedException(Exception):
    pass


SALT_ALPHABET = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890'


def decode(pk_str):
    # hasher = Hashids(salt=current_app.config['HASHIDS_SALT'],
    #                  min_length=8)
    # decoded_id = hasher.decode(pk)
    # if not decoded_id:
    #     raise DecodeFailedException(
    #         'Was not able to decode the given string')
    # else:
    #     return decoded_id[0]
    # Convert from unicode to standard str
    return int(base64.urlsafe_b64decode(str(pk_str))[5:])


def encode(pk):
    # hasher = Hashids(salt=current_app.config['HASHIDS_SALT'],
    #                  min_length=8)
    # return hasher.encode(pk)
    return base64.urlsafe_b64encode('tmaps' + str(pk))
