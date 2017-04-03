# TmServer - TissueMAPS server application.
# Copyright (C) 2016  Markus D. Herrmann, University of Zurich and Robin Hafen
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
    """Decode a hashed database ID so that it can be used
    when formulating SQL queries.

    Parameters
    ----------
    pk_str : str
        hashed database ID

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
        original database ID

    Returns
    ------
    str
        hashed database ID

    """
    return base64.urlsafe_b64encode('tmaps' + str(pk))
