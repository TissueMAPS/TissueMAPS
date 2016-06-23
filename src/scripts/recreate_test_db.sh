#!/bin/bash

dropdb tissuemaps_test
createdb tissuemaps_test
echo 'CREATE EXTENSION postgis;' | psql -d tissuemaps_test
