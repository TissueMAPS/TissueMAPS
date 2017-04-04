#!/bin/sh -e

# Install requirements
echo "Install required apt packages..."
sudo apt-get update
sudo apt-get -y install python-dev build-essential libssl-dev python-apt python-pip python-setuptools wget vim
sudo pip install --upgrade pip setuptools virtualenvwrapper pytest

# Setup Python virtual environment
echo "Create Python virtual environment..."
export WORKON_HOME=$HOME/.virtualenvs
. /usr/local/bin/virtualenvwrapper.sh
mkvirtualenv tmtest

# Install TissueMAPS Python packages
echo "Install tmdeploy package..."
pip install https://github.com/tissuemaps/tmdeploy/tarball/master#egg=tmdeploy
echo "Install tmclient package..."
pip install https://github.com/tissuemaps/tmclient/tarball/master#egg=tmclient

# Build Docker containers and start them in the background
echo "Build Docker containers..."
tm_deploy -v container build
echo "Start Docker containers..."
tm_deploy -v container start
echo "=> You can connect to the TissueMAPS server on port 8002"

exit 0


