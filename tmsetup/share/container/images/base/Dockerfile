FROM ubuntu:xenial

RUN apt-get update && apt-get -y install \
        aptitude \
        build-essential \
        man \
        git \
        libssl-dev \
        libffi-dev \
        python \
        python-apt \
        python-dev \
        python-pip \
        python-setuptools \
        sudo \
        tar \
        wget \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade \
        pip \
        setuptools \
        cryptography \
        ndg-httpsclient \
        pyopenssl \
        pyasn1 \
        urllib3 \
        dumb-init

RUN adduser --quiet --home /home/tissuemaps --shell /bin/bash tissuemaps && \
    usermod -a -G tissuemaps,sudo tissuemaps && \
    chown -R tissuemaps:tissuemaps /home/tissuemaps && \
    chmod 0775 /home/tissuemaps

RUN bash -c "echo 'tissuemaps ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers.d/tissuemaps"
