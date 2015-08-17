#!/bin/sh

dropdb tissuemaps
createdb tissuemaps
python manage.py create_tables
python manage.py populate_db
