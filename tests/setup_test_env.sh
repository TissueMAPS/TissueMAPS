#!/bin/bash

# Setup Python virtual environment
echo "Activate Python virtual environment"
export WORKON_HOME=$HOME/.virtualenvs
if [ ! -d $WORKON_HOME ]; then
    mkdir -p $WORKON_HOME
fi
source /usr/local/bin/virtualenvwrapper.sh
mkvirtualenv "tmtest_$(date +%F_%H-%M-%S)"

# Install TissueMAPS Python packages
echo "Install tmdeploy package"
pip install tmdeploy

echo "Install tmclient package"
pip install tmclient

# Build Docker containers and start them in the background
echo "Build Docker containers"
tm_deploy -v container build

echo "Start Docker containers"
tm_deploy -v container start

exit 0

