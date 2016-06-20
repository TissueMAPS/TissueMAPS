import json

from flask import request, jsonify

from tmaps.user import User
from tmaps.api import api
from tmaps.extensions import db


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
