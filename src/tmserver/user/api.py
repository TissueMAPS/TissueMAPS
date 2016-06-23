import json

from flask import request, jsonify

from tmserver.user import User
from tmserver.api import api
from tmserver.extensions import db


@api.route('/register', methods=['POST'])
def register():
    data = json.loads(request.data)
    password = data.get('password')
    username = data.get('username')
    email = data.get('email')

    u = User(name=username, password=password, email=email)
    db.session.add(u)
    db.session.commit()

    return jsonify({
        'id': u.id,
        'name': username,
        'email': email
    })
