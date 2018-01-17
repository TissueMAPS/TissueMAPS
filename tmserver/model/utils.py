# TmServer - TissueMAPS server application.
# Copyright (C) 2016  Markus D. Herrmann, University of Zurich and Robin Hafen
# Copyright (C) 2018  University of Zurich
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""Utility functions for dealing with data models."""
import base64


def decode_pk(pk_str):
    """
    Decode a database ID from its representation in GET and POST requests.

    The current external representation of database IDs is just the
    printed representation of the ID as a decimal number, but this
    function can decode also older encodings as base64-obfuscated
    strings.

    See :func:`encode_pk`.

    Parameters
    ----------
    pk_str : str
        external representation of database ID

    Returns
    ------
    int
        original database ID

    Raises
    ------
    ValueError
        when the hashed ID can't be decoded.
    """
    try:
        return int(pk_str)
    except (TypeError, ValueError):
        pass  # assume we've got an old base64-encoded thing
    # decode old base64-encoding
    try:
        return int(base64.urlsafe_b64decode(str(pk_str))[5:])
    except Exception as e:
        raise ValueError(
            'Cannot decode hashed primary key %s. '
            'Original exception: %s' % (pk_str, e))


def encode_pk(pk):
    """
    Encode a database id as a string.

    Currently the encoding is just the representation of `pk` as a
    string of decimal digits.  (Former versions of this function used
    to munge and base64-encode the ID to obfuscate it, but is no
    apparent reason to do so.)

    Parameters
    ----------
    pk : int
        original database ID

    Returns
    ------
    str
        hashed database ID
    """
    return ('%d' % pk)
