import base64


def decode_pk(pk_str):
    try:
        pk = int(base64.urlsafe_b64decode(str(pk_str))[5:])
    except Exception as e:
        raise ValueError(
            'Cannot decode hashed primary key %s. '
            'Original exception: %s' % (pk_str, str(e)))
    else:
        return pk


def encode_pk(pk):
    return base64.urlsafe_b64encode('tmaps' + str(pk))

