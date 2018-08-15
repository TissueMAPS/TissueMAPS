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
import json
from flask import request, jsonify

import tmlib.models as tm

from tmserver.api import api


# @api.route('/register', methods=['POST'])
# def register():
#     """
#     .. http:post:: /api/experiments/register

#         Registers a new :class:`User <tmlib.models.user.User>` in the database.

#         **Example request**:

#         .. sourcecode:: http

#             Content-Type: application/json

#             {
#                 "username": "testuser",
#                 "password": "XXX",
#                 "email": "testuser@gmail.com",
#             }

#         **Example response**:

#         .. sourcecode:: http

#             Content-Type: application/json

#             {
#                 "id": "MQ==",
#                 "name": "testuser",
#                 "email": "testuser@gmail.com",
#             }

#         :statuscode 200: no error

#     """
#     data = json.loads(request.data)
#     password = data.get('password')
#     username = data.get('username')
#     email = data.get('email')

#     with tm.utils.MainSession() as session:
#         u = tm.User(name=username, password=password, email=email)
#         session.add(u)

#         return jsonify({
#             'id': u.id,
#             'name': username,
#             'email': email
#         })
