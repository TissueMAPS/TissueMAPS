#!/bin/sh

# Needs uwsgi! (installable via $ sudo pip install uwsgi)
cd server && uwsgi --http :8080 --wsgi-file wsgi.py --master --processes 4 --threads 2 --stats 127.0.0.1:8081

