import json

from flask import request, jsonify

from tmserver.user import User
from tmserver.api import api


@api.route('/register', methods=['POST'])
def register():
    data = json.loads(request.data)
    password = data.get('password')
    username = data.get('username')
    email = data.get('email')

    with tm.utils.MainSession() as session:
        u = tm.User(name=username, password=password, email=email)
        session.add(u)

        return jsonify({
            'id': u.id,
            'name': username,
            'email': email
        })
