"""Utility functions for dealing with moodels."""
import base64


def decode_pk(pk_str):
    """Decode a hashed database id so that it can be used
    when formulating SQL queries.

    Parameters
    ----------
    pk_str : str
        Hashed database id.

    Returns
    ------
    int
        The original database id.

    Raises
    ------
    ValueError
        The hashed id can't be decoded.

    """
    try:
        pk = int(base64.urlsafe_b64decode(str(pk_str))[5:])
    except Exception as e:
        raise ValueError(
            'Cannot decode hashed primary key %s. '
            'Original exception: %s' % (pk_str, str(e)))
    else:
        return pk


def encode_pk(pk):
    """Encode a database id as a string such that it is not directly
    visible to the client

    Parameters
    ----------
    pk : int
        Database id

    Returns
    ------
    str
        Hashed database string

    """
    return base64.urlsafe_b64encode('tmaps' + str(pk))
