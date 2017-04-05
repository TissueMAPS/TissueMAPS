#!/bin/sh -e

# Install requirements
echo "Install required apt packages..."
sudo add-apt-repository \
       "deb [arch=amd64] https://download.docker.com/linux/ubuntu \
       $(lsb_release -cs) \
       stable"
sudo apt-get update
sudo apt-get -y install \
    python-dev \
    build-essential \
    libssl-dev \
    libffi-dev \
    python-apt \
    python-pip \
    python-setuptools \
    wget \
    curl \
    apt-transport-https \
    ca-certificates \
    docker-ce

echo "Install required pip packages..."
sudo pip install --upgrade \
    pip \
    setuptools \
    virtualenvwrapper \
    pytest


# Setup Python virtual environment
echo "Create Python virtual environment..."
export WORKON_HOME=$HOME/.virtualenvs
. /usr/local/bin/virtualenvwrapper.sh
mkvirtualenv tmtest

# Install TissueMAPS Python packages
echo "Install tmdeploy package..."
pip install tmdeploy

echo "Install tmclient package..."
pip install tmclient

# Build Docker containers and start them in the background
echo "Build Docker containers..."
tm_deploy -v container build

echo "Start Docker containers..."
tm_deploy -v container start

echo "=> You can connect to the TissueMAPS server on localhost port 8002"
exit 0


