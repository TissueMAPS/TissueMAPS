#!/bin/bash
echo "stopping web server"
sudo service nginx stop
echo "stopping application server"
sudo service uwsgi stop
