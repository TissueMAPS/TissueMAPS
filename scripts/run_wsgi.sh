#!/bin/sh

# Needs uwsgi! (installable via $ sudo pip install uwsgi)
uwsgi --http :5002 --wsgi wsgi:app --master --processes 2 --threads 5 --stats 127.0.0.1:5003 -H ~/.virtualenvs/tmaps

