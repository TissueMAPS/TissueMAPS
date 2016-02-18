#!/bin/sh

# This script is used to recreate databases and automatically insert sample data.
# Usage:
#
# $ sh scripts/recreate_db.sh path/to/sample_data.yaml
#
# The sample_data.yaml file can be structured like this:
#
# ---
# records:
#     - class: User
#       args:
#           name: testuser
#           email: testuser@something.com
#           location: /Users/robin/Dev/TissueMAPS/expdata
#           password: '123'
#     - class: User
#       args:
#           name: testuser2
#           email: testuser2@something.com
#           location: /Users/robin/Dev/TissueMAPS/expdata/somethingelse
#           password: '123'
#     - class: Experiment
#       args:
#           name: 150316-30min-PBS
#           description: Very nice exp
#           owner:
#               class: User
#               lookup_props:
#                   name: testuser
#           location: /Users/robin/Dev/TissueMAPS/expdata/150316-30min-PBS
#           microscope_type: visiview
#           plate_format: 96
#
# Each entry in the records list will be checked for a "class" and a "args" attribute.
# "args" is a dictionary of constructor arguments.
# Values can be objects themselves. In this case they also need a "class"
# attribute and a "lookup_props" entry that specifies keyword arguments passed to
# Query.filter_by.
# The returned object should be unique. Also, make sure that the object is created
# before it is referenced somewhere else (i.e. it has to be listed
# in the records list before the reference is made)

dropdb tissuemaps
createdb tissuemaps
python manage.py db create_tables
python manage.py db insert_data "$1"
