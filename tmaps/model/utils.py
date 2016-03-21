import base64


def decode_pk(pk_str):
    return int(base64.urlsafe_b64decode(str(pk_str))[5:])


def encode_pk(pk):
    return base64.urlsafe_b64encode('tmaps' + str(pk))

