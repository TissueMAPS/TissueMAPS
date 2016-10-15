
************
Installation
************

.. _clients:

Clients
=======

Using `TissueMAPS` clients is straight forward, once the `server`_ is set up.
Users can interact with the program via a standard web browser (tested with `Chrome <https://www.google.com/chrome/>`_, `Firefox <https://www.mozilla.org/en-US/firefox/new/>`_ and `Safari <http://www.apple.com/safari/>`_) without the need to install any additional software locally.
Further client implementations in various languages are available via the `TmClient <https://github.com/TissueMAPS/TmClient>`_ repository.

.. _python-client:

Python client
-------------

The `tmclient` Python package provides an interface for uploading and downloading data via the command line.

.. _non-python-requirements:

Requirements
^^^^^^^^^^^^

* `Python <https://www.python.org/>`_ (version 2.7): Many platforms are shipped with Python already pre-installed. If not, it can downloaded from `python.org <https://www.python.org/downloads/>`_. We recommend using version 2.7.9 or higher.
* `Pip <https://pip.pypa.io/en/stable/>`_: The Python package manager is automatically installed with Python distributions downloaded from python.org. Otherwise, it can be installed with the `get-pip.py <https://bootstrap.pypa.io/get-pip.py>`_ script.
* `OpenCV <http://opencv.org/>`_ (version 3.1): Prebuild binaries for different platforms are available for download on `opencv.org <http://opencv.org/downloads.html>`_. Detailed instructions for building the latest version from source can be found in the `online documentation <http://docs.opencv.org/3.1.0/df/d65/tutorial_table_of_content_introduction.html>`_. Packages are also available via `homebrew <https://github.com/Homebrew/homebrew-science/blob/master/opencv3.rb>`_ on `MacOSX` or cross-platform via `anaconda <https://anaconda.org/menpo/opencv3>`_. Note that, when using a virtual environment, the Python bindings need to be  manually copied or linkied.


Installation
^^^^^^^^^^^^

The `tmlib` Python package can be installed via `pip`::

    pip install git+https://github.com/TissueMAPS/TmClient.git


.. _matlab-client:

Matlab client
-------------

Requirements
^^^^^^^^^^^^

* `Matlab <https://mathworks.com/products/matlab/>`_ (version 2014b or later): Requires `RESTful web services <https://ch.mathworks.com/help/matlab/internet-file-access.html>`_, which were introduced in version 2014b.


Installation
^^^^^^^^^^^^

To be able to import the `tmclient` Matlab package, the source code needs to be downloaded from Github.
To this end, clone the `TmClient <https://github.com/TissueMAPS/TmClient>`_ repository using the `git <https://git-scm.com/>`_ command line interface on Linux/MacOSX or `Git Bash <https://git-for-windows.github.io/>`_ on Windows::

    git clone https://github.com/TissueMAPS/TmClient.git $HOME/tmclient

The path to the local copy of the Matlab code needs to be added to the Matlab search path, by either using a ``startup.m`` file or setting the ``MATLABPATH`` environment variable. For further information please refer to the `Matlab online documentation <https://mathworks.com/help/matlab/matlab_env/add-folders-to-matlab-search-path-at-startup.html>`_.


.. _r-client:

R client
--------

Requirements
^^^^^^^^^^^^

* `R <https://www.r-project.org/>`_ (version 3.0.2 or higher): R is available for `download <https://cran.r-project.org/mirrors.html>`_.
* `devtools <https://cran.r-project.org/web/packages/devtools/README.html>`_: The R package can be downloaded from CRAN: ``install.packages("devtools")``.


Installation
^^^^^^^^^^^^

The `tmclient` R package can be installed via the R console using the `devtools` package:

.. code:: R

    library(devtools)
    install_github("TissueMAPS/TmClient")

.. _server:

Server
======

The server backend is designed for `UNIX`-based operating systems. It has been successfully deployed in production on `Ubuntu 14.04 Trusty <http://releases.ubuntu.com/14.04/>`_ and used for development on `MacOSX 10.10.5 Yosemite <https://support.apple.com/kb/DL1833?locale=en_US>`_. It won't work on a Windows platform.

The different servers might be all installed on the same machine or on different VMs, depending on available resources and expected workloads. For simplicity, installation instructions are given here for use on `localhost`.
Below you find the invidual installation and configuration steps required to manually set up a `TissueMAPS` server together with all the required components. In the `automatic setup <automatic-setup>`_ section, you'll find instructions on how to do this in a fully automated way.

.. _web-server:

Web server
----------

The `TmUI <https://github.com/TissueMAPS/TmUI>`_ repository hosts the code for the `AngularJS <https://angularjs.org/>`_ app. It is written to large extends in `TypeScript <https://www.typescriptlang.org/>`_ and managed by `Gulp <http://gulpjs.com/>`_.
The `HTTP` server serves the app (`HTML <http://www.w3schools.com/html/html_intro.asp>`_ templates and built `Javascript <http://www.w3schools.com/js/js_intro.asp>`_ code) to clients.

Requirements
^^^^^^^^^^^^

* `NodeJs <https://nodejs.org/en/>`_: Also provides its package manager `npm <https://www.npmjs.com/>`_.

    On Ubuntu::

        curl -sL https://deb.nodesource.com/setup_6.x | sudo -E bash -
        sudo apt-get -y install nodejs

    On MacOSX::

        brew install node

* `Git <https://git-scm.com/>`_:

    On Ubuntu::

        sudo apt-get install git

    On MacOSX::

        brew install git

* `NGINX <https://www.nginx.com/>`_ (for production deployment):

    On Ubuntu::

        sudo apt-get -y install nginx

    On MacOSX::

        brew install nginx


Installation
^^^^^^^^^^^^

Clone the `TmUI <https://github.com/TissueMAPS/TmUI>`_ repository (including submodules) from Github and change the current directory::

    git clone --recursive https://github.com/TissueMAPS/TmUI.git $HOME/tmclient
    cd $HOME/tmui/src

Install `node` packages::

    npm install

Install `bower <https://bower.io/>`_ packages::

    node_modules/bower/bin/bower install

Build cliet code for production deployment::

    node_modules/gulp/bin/gulp.js build --production

This will create a ``build`` subdirectory. The contents of this directory can now be served by a separate HTTP web server, such as `NGINX`.


Configuration
^^^^^^^^^^^^^

When using `NGINX`, create an application-specific site and set the path to the ``build`` directory in ``/etc/nginx/sites-available/tissuemaps``::

    server {
        listen 80;
        # server_name tissuemaps.org

        access_log /var/log/nginx/tissuemaps-access.log;
        error_log /var/log/nginx/tissuemaps-error.log;

        # all non-api requests are file requests and should be served
        # from the built client dir
        root /home/ubuntu/tmui/src/build;
        location / {
            try_files $uri $uri/ @proxy;
        }

        # all other request (e.g. with /api or /auth prefix) to uwsgi
        # listening on the unix socket nginx-comm.sock
        location @proxy {
            include uwsgi_params;
            uwsgi_pass unix:/home/ubuntu/.tmaps/uwsgi.sock;
        }
    }

and enable the site by creating the following softlink:

for development set the ``tissuemaps`` site as default::

    sudo mv /etc/nginx/sites-available/default /etc/nginx/sites-available/orig_default
    sudo ln -s /etc/nginx/sites-available/tissuemaps /etc/nginx/sites-available/default

for production deployment::

    sudo ln -s /etc/nginx/sites-available/tissuemaps /etc/nginx/sites-enabled/tissuemaps

Also set the following application-specific parameters in ``/etc/nginx/conf.d/tissuemaps.conf``::

    uwsgi_read_timeout 3600;
    uwsgi_buffering off;
    client_max_body_size 10000M;


.. _application-server:

Application server
------------------

The application server communicates between the web server and the Python web application, using the `Web Server Gateway Interface (WSGI) specification <https://wsgi.readthedocs.io/en/latest/>`_.
Here we use a Unix socket, which uses the with `WSGI` protocol, instead of a network port for communication with the `NGINX` proxy server. This works when all of the components are operating on a single machine, but needs to be changed for a multi-VM configuration.

Requirements
^^^^^^^^^^^^

* `Python <https://www.python.org/>`_ (version 2.7): Ubuntu (up to version 14.04) and MacOSX come with Python included. However, installing a newer version (2.7.9 or higher) is recommended. For compatibility, all machines should have the same Python version installed! On MacOSX we also need the `Homebrew` version.
* `Pip <https://pip.pypa.io/en/stable/>`_: The Python package manager is typically already installed with the Python distributions.

    On Ubuntu::

        sudo add-apt-repository ppa:fkrull/deadsnakes-python2.7
        sudo apt-get update
        sudo apt-get install python2.7

        sudo apt-get -y install python-pip python-dev build-essential
        sudo pip install --upgrade pip

    On MacOSX::

        brew install python


Installation
^^^^^^^^^^^^

If you don't install the application on a dedicated machine, we recommend using a virtual environment.

To this end, install `virtualenv <https://virtualenv.readthedocs.org/en/latest/>`_ and `virtualenvwrapper <https://virtualenvwrapper.readthedocs.org/en/latest/>`_ and set up your environment::

    sudo pip install virtualenv virtualenvwrapper

Execute the following lines and add them to your ``.bash_profile`` file::

    export WORKON_HOME=$HOME/.virtualenvs
    source /usr/local/bin/virtualenvwrapper.sh

Create a ``tissuemaps`` project for all `TissueMAPS` dependencies::

    mkvirtualenv tissuemaps

You can later activate the environment as follows::

    workon tissuemaps

.. warning::

    A coexisting `anaconda <http://docs.continuum.io/anaconda/pkg-docs>`_ installation doens't play nice with virtual environments and will create problems; see `potential solution <https://gist.github.com/mangecoeur/5161488>`_. It might also create issues with Python bindings installed by other package managers.

`uWSGI` can be installed via the Python package manager `pip`::

    sudo pip install uwsgi

On MacOSX it can also be installed via `homebrew`, which can then be conviently controlled via `services <https://github.com/Homebrew/homebrew-services>`::

    brew install uwsgi


Configuration
^^^^^^^^^^^^^

Create a direcotory for application-specific configurations::

    mkdir $HOME/.tmaps

Configure `uWSGI` in ``$HOME/.tmaps/uwsgi.ini``:

.. code-block:: ini

    [uwsgi]
    module = tmserver.wsgi:app
    http-socket = :8080
    logto = $(HOME)/.tmaps/uwsgi.log
    socket = $(HOME)/.tmaps/uwsgi.sock
    chmod-socket = 666
    vacuum = true
    die-on-term = true
    master = true
    processes = 16
    gevent = 100

Ensure that it runs in `gevent <http://www.gevent.org/>`_ mode and
adapt configurations according on available computational resources.

When working with a virtual environment, include the path to the project:

.. code-block:: ini

    home = $(VIRTUALENVWRAPPER_HOOK_DIR)/tissuemaps

Then create an upstart script in ``$HOME/.tmaps/uwsgi.sh``:

.. code-block:: bash

    #!/bin/bash
    source $HOME/.bash_profile
    uwsgi --ini $HOME/.tmaps/uwsgi.ini

and set the path to the script in the service definition file ``/etc/init/uwsgi.conf`` (exemplified here for ``ubuntu`` user)::

    description "uWSGI server instance configured to serve TissueMAPS"

    start on runlevel [2345]
    stop on runlevel [!2345]

    setuid ubuntu
    setgid ubuntu

    chdir /home/ubuntu/.tmaps
    exec env HOME=/home/ubuntu bash uwsgi.sh

.. _application:

Application
-----------

The actual Python web application is implemented in the `Flask <http://flask.pocoo.org/>`_ micro-framework.


Requirements
^^^^^^^^^^^^

* `PostgreSQL <http://postgresxl.org/>`_ (version 9.6): PostgreSQL is available on Ubuntu by default, but we want a more recent version with improved performanced. On MacOSX the `PostgresApp <http://postgresapp.com/>`_ could be used alternatively.

    An apt repository is available for `download <https://www.postgresql.org/download/linux/ubuntu/>`_ on Ubuntu::

        sudo sh -c "echo 'deb http://apt.postgresql.org/pub/repos/apt/ trusty-pgdg main' > /etc/apt/sources.list.d/pgdg.list"

        wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -
        sudo apt-get update

        sudo apt-get -y install postgresql-9.6
        sudo apt-get -y install postgresql-9.6-postgis-2.2 postgresql-9.6-postgis-scripts postgresql-contrib-9.6 postgresql-server-dev-all postgresql-client

        sudo apt-get -y install python-psycopg2

    On MacOSX::

        brew tap petere/postgresql
        brew install postgresql-9.6 && brew link -f postgresql-9.6
        brew install pex
        brew install gettext && brew link -f gettext
        pex init
        pex -g /usr/local/opt/postgresql-9.6 install postgis

* `OpenCV <`http://opencv.org/>`_ (version 3.1):

    On Ubuntu the `apt-get` package manager only provides version 2.4. Version 3.1 needs to be `build from source <http://docs.opencv.org/3.1.0/d7/d9f/tutorial_linux_install.html>`_::

        git clone https://github.com/Itseez/opencv.git $HOME/opencv
        cd $HOME/opencv
        mkdir build && cd build

        sudo pip install numpy

        sudo apt-get -y install cmake
        cmake -D CMAKE_BUILD_TYPE=RELEASE -D CMAKE_INSTALL_PREFIX=/usr/local ../
        make -j4
        sudo make install && sudo ldconfig

    On MacOSX::

        brew tab homebrew/science
        brew install opencv3
        echo /usr/local/opt/opencv3/lib/python2.7/site-packages >> /usr/local/lib/python2.7/site-packages/opencv3.pth

    Build `OpenCV` globally and create softlinks for the Python bindings to use it within a virtual environment (exemplified for ``tissuemaps`` project):

    On Ubuntu::

        cd $VIRTUALENVWRAPPER_HOOK_DIR/tissuemaps/lib/python2.7/site-packages
        ln -s /usr/local/lib/python2.7/dist-packages/cv2.so cv2.so

    On MacOSX::

        cd $VIRTUALENVWRAPPER_HOOK_DIR/tissuemaps/lib/python2.7/site-packages/
        ln -s /usr/local/lib/python2.7/site-packages/opencv3.pth opencv3.pth

* `HDF5 <https://www.hdfgroup.org/HDF5/>`_:

    On Ubuntu::

        sudo apt-get -y install libhdf5-dev hdf5-tools

    On MacOSX::

        brew tab homebrew/science
        brew install hdf5

* `Bio-Formats command line tools <http://www.openmicroscopy.org/site/support/bio-formats5.2/users/comlinetools/>`_ (version 5.1 or higher):

    On Ubuntu::

        sudo apt-get -y install openjdk-7-jdk
        sudo apt-get install unzip
        curl -s -o $HOME/bftools.zip https://downloads.openmicroscopy.org/bio-formats/5.2.3/artifacts/bftools.zip
        unzip bftools.zip
        echo 'export PATH=$PATH:$HOME/bftools' >> $HOME/.bash_profile

    On MacOSX::

        brew tab ome/alt
        brew install bioformats51

* `Spark <http://spark.apache.org/>`_ (version 2.0): Requires installation with support for `YARN <http://hadoop.apache.org/docs/stable/hadoop-yarn/hadoop-yarn-site/YARN.html<Paste>>`_ for running Spark on a cluster as well as `Hive <https://hive.apache.org/>`_ and `JDBC <http://docs.oracle.com/javase/tutorial/jdbc/overview/index.html>`_ for `Spark SQL <http://spark.apache.org/docs/latest/sql-programming-guide.html#overview>`_ integration. It is important to `build <http://spark.apache.org/docs/latest/building-spark.html#specifying-the-hadoop-version>`_ Spark againgst the `HDFS <http://hadoop.apache.org/docs/r1.2.1/hdfs_design.html>`_ version available in your cluster environment, since `HDFS` is not cross compatible across versions. Pyspark further requires the same minor version of Python in both drivers and workers.

    On Ubuntu::

        sudo apt-get install openjdk-7-jdk
        export JAVA_HOME=/usr/lib/jvm/java-1.7.0-openjdk-amd64

        sudo apt-get -y install maven
        export MAVEN_OPTS="-Xmx2g -XX:MaxPermSize=512M -XX:ReservedCodeCacheSize=512m"

        sudo wget http://d3kbcqa49mib13.cloudfront.net/spark-2.0.1.tgz
        tar -xvzf spark-2.0.1.tgz && mv spark-2.0.1 spark
        sudo apt-get update

        cd spark
        ./build/mvn -Pyarn -Phadoop-2.7 -Dhadoop.version=2.7.1 -Phive -Phive-thriftserver -DskipTests clean package

        echo 'export PATH=$PATH:$HOME/spark/bin' >> $HOME/.bash_profile

    On MacOSX::

        brew install apache-spark

* other:

    On Ubuntu::

        sudo apt-get -y install libxml2-dev libxslt1-dev zlib1g-dev
        sudo apt-get -y install libgeos-dev


Installation
^^^^^^^^^^^^

Download the server code from Github::

    git clone https://github.com/TissueMAPS/TmServer.git $HOME/tmserver

Install the `tmserver` Python package via `pip`::

    cd $HOME/tmserver
    pip install .

You may want to install `TissueMAPS` packages in developer mode to be able to modify code locally. To this end, you can clone and install repositories in ``$HOME/tmserver/requirements/requirements-git.txt`` manually.


Configuration
^^^^^^^^^^^^^

PostgreSQL
~~~~~~~~~~

Create a database cluster for a given ``data_directory`` and start the server (here demonstrated for `PostgreSQL` version 9.6 with the default ``data_directory`` - it might have already been done automatically upon installation):

    On Ubuntu (as ``postgres`` user)::

        sudo su - postgres
        /usr/lib/postgresql/9.6/bin/initdb -D /var/lib/postgresql/9.6/main
        /usr/lib/postgresql/9.6/bin/pg_ctl -D /var/lib/postgresql/9.6/main -l logfile restart

    On MacOsX (as current user)::

        /usr/local/opt/postgresql-9.6/bin/initdb -D /usr/local/var/lib/postgresql/9.6/main
        /usr/local/opt/postgresql-9.6/bin/pg_ctrl -D /usr/local/var/lib/postgresql/9.6/main -l logfile restart

On MacOSX you may want to add the `PostgreSQL` executables to the ``$PATH`` in your ``.bash_profile`` file::

        export PATH=$PATH:/usr/local/opt/postgresql-9.6/bin
        export MANPATH=$MANPATH:/usr/local/opt/postgresql-9.6/share/man

On Ubuntu ``service`` can also be used to start and stop the database server::

        sudo service postgresql restart

Configure postgres in ``/etc/postgresql/9.6/main/postgresql.conf``:

.. code-block:: sql

    listen_addresses = '*'
    host  all  all  .0.0.0/0  md5

Enter `psql` console:

    On Ubuntu (as ``postgres`` user)::

        sudo -u postgres psql postgres

    On MacOSX (as current user)::

        psql postgres

    On MacOSX the postgres user has to be created first:

.. code-block:: sql

    CREATE USER postgres;
    ALTER USER postgres WITH SUPERUSER;

and change password for ``postgres`` user (on MacOSX you need to create the ``postgres`` user first):

.. code-block:: sql

    ALTER USER postgres WITH PASSWORD 'XXX';

and create the ``tissuemaps`` database and `postgis <http://www.postgis.net/>`_ extension:

.. code-block:: sql

    CREATE DATABASE tissuemaps;
    \connect tissuemaps;
    CREATE EXTENSION postgis;

Now, you should be able to connect to the database as ``postgres`` user with your new password::

    psql -h localhost tissuemaps postgres

It's convenient to use a `pgpass file <https://www.postgresql.org/docs/current/static/libpq-pgpass.html>`_ to be able to connect to the database without having to type the password::

    echo "*:5432:tissuemaps:postgres:XXX" > $HOME/.pgpass
    chmod 0600 $HOME/.pgpass

When using a mounted filesystem for data storage, you can create a symlink to ``data_dirctory`` or use an alternative directory. Make sure, however, to set the correct permissions for the parent directory of the desired data directory. For more information please refer to the PostgreSQL online documentation on `file locations <https://www.postgresql.org/docs/current/static/runtime-config-file-locations.html>`_ and `creation of a new database cluster <https://www.postgresql.org/docs/9.6/static/app-initdb.html>`_.


Create the `TissueMAPS` configuration file ``.tmaps/tissuemaps.cfg``::

    tm_create_config

Set the ``db_password`` parameter (replace ``XXX`` with the actual password):

.. code-block:: ini

    [DEFAULT]
    db_password = XXX

Create the tables in the ``tissuemaps`` database::

    tm_create_tables


Apache Spark (optional)
~~~~~~~~~~~~~~~~~~~~~~~

In case you have access to a `YARN <http://hadoop.apache.org/docs/stable/hadoop-yarn/hadoop-yarn-site/YARN.html>`_ cluster, copy the configuration files to each machine to which a tool requests might be submitted and provide the path to the local copy of the files via the environment variable ``YARN_CONF_DIR``, e.g.::

    echo 'export YARN_CONF_DIR=/etc/hadoop' >> $HOME/.bash_profile

The `configuration files <http://hadoop.apache.org/docs/stable/hadoop-project-dist/hadoop-common/ClusterSetup.html#Configuring_Hadoop_in_Non-Secure_Mode>`_ are required to connect to the cluster resource manager and the HDFS.

.. Since `TissueMAPS` uses `PySpark <http://spark.apache.org/docs/latest/api/python/index.html<Paste>>`_, the required python files need to be distributed to the cluster. To facilitate deployment, create an `.egg` for the package::

..     cd $HOME/tmtoolbox
..     python setup.py bdist_egg

.. And add the path of the `.egg` file to the `TissueMAPS` configuration in ``$HOME/.tmaps/tissuemaps.cfg``:

.. .. code-block:: ini

..     [tmserver]
..     spark_tmtoolbox_egg = %(home)s/tmtoolbox/dist/tmtoolbox-0.0.1-py2.7.egg


GC3Pie
~~~~~~

Create an example configuration file by calling any `GC3Pie` command, e.g.::

    $ gserver

This will create the file ``$HOME/.gc3/gc3pie.conf``. Modify it according to your computational infrastructure. For more information please refer to the `GC3Pie online documentation <http://gc3pie.readthedocs.org/en/latest/users/configuration.html>`_:

.. code-block:: ini

    [auth/noauth]
    type=none

    [resource/localhost]
    enabled=yes
    type=shellcmd
    auth=noauth
    transport=local
    # max_cores sets a limit on the number of cuncurrently-running jobs
    max_cores=4
    max_cores_per_job=4
    # adjust the following to match the features of your local computer
    max_memory_per_core=4 GB
    max_walltime=48 hours
    architecture=x64_64
    # When True, the shellcmd backend will discover the actual
    # architecture, the number of cores and the total memory of the
    # machine and will ignore the values found on the configuration
    # file. Default is `False`
    override=yes


.. _startup:

Startup
-------

Now that we have (hopefully) are parts installed and configured, the servers can be started.


Production mode
^^^^^^^^^^^^^^^

For production, web server (`NGINX`) and application server (`uWSGI`) need to be started:

On Ubuntu::

    sudo service nginx start
    sudo service uwsgi start


Development mode
^^^^^^^^^^^^^^^^

For local developement and testing `NGINX` and `uWSGI` are not required.

The `tmserver` package provides a `development application server <http://flask.pocoo.org/docs/0.11/server/#server>`_::

    tmserver

The client installation also provides a `development web server <https://www.npmjs.com/package/gulp-webserver>`_ to dynamically build client code with live reload functionality::

    cd $HOME/tmui/src
    node_modules/gulp/bin/gulp.js

This will automatically start the server on localhost (port 8002).

Both dev servers provide live reload functionality. They will auto-watch files and rebuild the code upon changes, which is useful for local development and testing.


.. _automated-server-deployment:

Automated server deployment
---------------------------

Manual installation and configuration, as described above, is feasible for a single machine.
However, when running `TissueMAPS` in a multi-node cluster setup, this process become labor intensive and error-prone.
The `TmPlaybooks <https://github.com/TissueMAPS/TmPlaybooks>`_ repository provides automated installation and configuration routines in form of `Ansible playbooks <http://docs.ansible.com/ansible/playbooks.html>`_ to setup `TissueMAPS` on cloud infrastructures.

Getting started
^^^^^^^^^^^^^^^

We launch the first VM instance manually. It will be used to carry out the subsequent automated creation and deployment steps and afterwards host the `Ganglia <http://ganglia.info/>`_ server to monitor the created cluster.

Requirements
^^^^^^^^^^^^

* `Git <https://git-scm.com/>`_::

    sudo apt-get -y install git


* `Python <https://www.python.org/>`_ (version 2.7) and the package manager `Pip <https://pip.pypa.io/en/stable/>`_::

    sudo add-apt-repository ppa:fkrull/deadsnakes-python2.7
    sudo apt-get update
    sudo apt-get -y install python2.7

    sudo apt-get -y install build-essential python-pip python-dev
    sudo pip install --upgrade pip

* `Ansible <https://www.ansible.com/>`_::

    sudo apt-get install software-properties-common
    sudo apt-add-repository ppa:ansible/ansible
    sudo apt-get update
    sudo apt-get -y install ansible

* `Elasticluster <http://gc3-uzh-ch.github.io/elasticluster/>`_::

    sudo apt-get -y install gcc g++ libc6-dev libffi-dev libssl-dev
    git clone https://github.com/gc3-uzh-ch/elasticluster.git ~/elasticluster
    cd ~/elasticluster && pip install .


Installation & Configuration
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Create a `ssh` key-pair and upload it the public key ``~/.ssh/id_rsa.pub`` to your cloud provider (call the key "elasticluster")::

    ssh-keygen
    ssh-agent bash
    ssh-add ~/.ssh/id_rsa

Launch a virtual machine (VM) (here called ``tissuemaps-monitor``) and connect to it via SSH using the created key-pair.

This instance will be used to run the setup and deployment steps for the creation of the `TissueMAPS` cluster. It will further host the `Ganglia <http://ganglia.info/>`_ server for monitoring the different components of the cluster.

On this instance, clone the `TmSetup <https://github.com/TissueMAPS/TmSetup>`_ repository from Github::

    git clone https://github.com/TissueMAPS/TmSetup.git ~/tmsetup

and modify the `Ansible inventory <http://docs.ansible.com/ansible/intro_inventory.html>`_ file ``/etc/ansible/hosts`` as described below.

.. TODO: create group_vars for postgresql_server, ganglia_server and tissuemaps_cluster hosts

Now, launch two additional VM instances (here called ``tissuemaps-web`` and ``tissuemaps-compute``) and specify the addresses of these two `hosts` in the inventory file:

.. code-block:: ini

    [tissuemaps_web]
    tissuemaps-web ansible_ssh_host=XXX ansible_ssh_user=ubuntu

    [tissuemaps_compute]
    tissuemaps-compute ansible_ssh_host=XXX ansible_ssh_user=ubuntu

These two instances are only temporarly required. They will be used to install and configure the `TissueMAPS` code and create `snapshots <https://en.wikipedia.org/wiki/Snapshot_(computer_storage)>`_, which can later be used to quickly boot multiple machines in the cluster building process (see below).

In case you don't want to create a multi-node `TissueMAPS` cluster, but use only a single machine to host all the different components, you simply need to create one instance (here called ``tissuemaps``) and place the same `host` into each `Ansible group <http://docs.ansible.com/ansible/intro_inventory.html#hosts-and-groups>`_:

.. code-block:: ini

    [tissuemaps_web]
    tissuemaps ansible_ssh_host=XXX ansible_ssh_user=ubuntu

    [tissuemaps_compute]
    tissuemaps ansible_ssh_host=XXX ansible_ssh_user=ubuntu

When using a single-node setup, the datbase also needs to be set up on the same `host`. To this end, extend the inventory file as follows:

.. code-block:: ini

    [postgresql_server]
    tissuemaps ansible_ssh_host=XXX ansible_ssh_user=ubuntu

    [postgresql_server:vars]
    db_password=XXX

and run the respective playbook::

    ansible-playbook -v  ~/tmsetup/playbooks/database.yml

Now, you can run the playbook to configure the ``tissuemaps`` host(s)::

    ansible-playbook -v  ~/tmsetup/playbooks/tissuemaps.yml

and create a snapshot of the created image(s). The ``tissuemaps-compute`` and ``tissuemaps-web`` instances (or the single ``tissuemaps`` instance) can now be terminated.

In case you chose a single-node setup (one VM hosting all components), you are already done. You can launch new VM instances from the created image. The image is configured such that it will automatically start all the servers upon booting the instance. To access the `TissueMAPS` user interface, make sure you use a security group that allows `HTTP` access and enter the IP address of the generated instance into the browser address bar.

The following section describes the setup of a multi-node `TissueMAPS` grid using `elasticluster`. In this grid, different components of the application are distributed across multiple dedicated VMs for scaling up. The setup process of the distributed architecture can be `configured <http://elasticluster.readthedocs.io/en/latest/configure.html>`_ in the ``~/.elasticluster/config`` file.

First, you need to specify your cloud provider and login details. `Elasticluster` supports several public and private cloud providers. Here we demonstrate the setup procedure for the `OpenStack <http://www.openstack.org/>`_-based `ScienceCloud <https://www.s3it.uzh.ch/en/scienceit/infrastructure/sciencecloud.html>`_ at University of Zurich:

.. code-block:: ini

    [cloud/sciencecloud]
    provider=openstack
    auth_url=https://cloud.s3it.uzh.ch:5000/v2.0
    username=XXX
    password=XXX
    project_name=XXX
    request_floating_ip=False

    [login/ubuntu]
    image_user=ubuntu
    image_user_sudo=root
    image_sudo=True
    user_key_name=elasticluster
    user_key_private=~/.ssh/id_rsa
    user_key_public=~/.ssh/id_rsa.pub

`Elasticluster` automates setup and configuration of the different ``cluster`` components of the `TissueMAPS` grid. The program launches virtual machine instances (called ``nodes``) as specified in each ``cluster`` section and then configures these `hosts` using `Ansible <https://www.ansible.com/>`_ as specified in the corresponding ``setup`` section. One can specify different `classes` of ``nodes`` and assign each `class` to one or more `host <http://docs.ansible.com/ansible/intro_inventory.html#hosts-and-groups>`_ ``groups``. `Elasticluster` then applies all `Ansible roles <http://docs.ansible.com/ansible/playbooks_roles.html>`_ (set of configuration tasks defined in the `elasticluster` repository) that were assigned to the allocated ``groups``. Custom playbooks, not available via the `elasticluster` repository, can be included via the ``playbook_path`` setting.

For the example given below, all ``nodes`` of the "slurm" ``cluster`` assigned to `class` ``slurm_workers`` will be setup with playbooks where the specified `hosts` match either ``slurm_workers`` or ``ganglia_monitor``.


In the following we go through the the creation of the individual components of a `TissueMAPS` cluster.

* `PostgreSQL <https://www.postgresql.org/>`_ database:

    .. code-block:: ini

        [setup/postgresql]
        provider=ansible
        postgresql_server_groups=postgresql_server,ganlia_monitor
        playbook_path=~/tmsetup/src/playbooks/database.yml
        master_var_db_password=XXX
        global_var_cluster_name=postgresql
        global_var_cluster_owner=XXX
        global_var_cluster_location=XXX

        [cluster/postgresql]
        cloud=sciencecloud
        login=ubuntu
        setup_provider=postgresql
        ssh_to=master
        postgresql_server_nodes=1
        postgresql_server_volumes=XXX


NOTE: We have also tested the `PostgresXL <http://postgresxl.org/>`_ database cluster, but were not satisfied with its performance and stability. In the future, the database might be scaled out using a `Citus <https://docs.citusdata.com/en/v5.2/aboutcitus/what_is_citus.html>`_ cluster. However, `citusdb` doesn't support all `PostgreSQL` features and will require changes in the `TissueMAPS` API. As of version 9.6 `PostgreSQL` optionally parallelizes (select) queries over CPUs, which can already give very good performance in our experience (even with hundreds of concurrently reading/writing compute nodes).


* `SLURM <http://slurm.schedmd.com/>`_ cluster to run custom batch compute jobs:

    .. code-block:: ini

        [setup/slurm]
        provider=ansible
        frontend_groups=slurm_master,ganlia_monitor
        slurm_worker_groups=slurm_workers,ganlia_monitor
        global_var_slurm_selecttype=select/cons_res
        global_var_slurm_selecttypeparameters=CR_Core_Memory
        global_var_cluster_name=slurm
        global_var_cluster_owner=XXX
        global_var_cluster_location=XXX

        [cluster/slurm]
        cloud=sciencecloud
        login=ubuntu
        setup_provider=slurm
        ssh_to=frontend
        frontend_nodes=1
        slurm_worker_nodes=4  # grow cluster in small batches
        security_group=XXX

        [cluster/slurm/frontend]
        # The frontend node also hosts the TissueMAPS server.
        # It requires an image with the "tmserver" package installed as well
        # as the web (NGINX) and application (uWSGI) servers installed and configured.
        # It further requires a network that allows incomging HTTP connections in
        # addition to SSH. Since it has to handle a potentially large number of
        # client request, we also use a beeg flava.
        image_id=tissuemaps-web
        flavor=XXX  # 16cpu-64ram-hpc
        network_ids=XXX

        [cluster/slurm/slurm_worker]
        image_id=tissuemaps-compute
        flavor=XXX  # 4cpu-16ram-hpc
        network_ids=XXX

NOTE:  We have implemented fair `scheduling <http://slurm.schedmd.com/sched_config.html>`_, based on `SLURM accounts <http://slurm.schedmd.com/accounting.html>`_. To enable this functionality, create an account for each `TissueMAPS` user using the provided `create_slurm_account.sh <>`_ script.


* `GlusterFS <https://www.gluster.org/>`_ cluster that serves a distributed filesystem:

    .. code-block:: ini

        [setup/glusterfs]
        provider=ansible
        glusterfs_server_groups=glusterfs_server,ganlia_monitor
        server_var_gluster_replicas=2
        server_var_gluster_stripes=1
        global_var_cluster_name=glusterfs
        global_var_cluster_owner=XXX
        global_var_cluster_location=XXX

        [cluster/glusterfs]
        cloud=sciencecloud
        login=ubuntu
        setup_provider=glusterfs
        glusterfs_server_nodes=8
        glusterfs_server_volumes=XXX
        # Clients have already been built (slurm_workers)
        ssh_to=server
        security_group=XXX  # default
        image_id=XXX
        flavor=XXX  # 32
        network_ids=XXX


* `YARN <https://hadoop.apache.org/docs/r2.7.2/hadoop-yarn/hadoop-yarn-site/YARN.html>`_ cluster to run `Apache Spark <http://spark.apache.org/docs/latest/running-on-yarn.html<Paste>>`_ map-reduce compute jobs (optional - will only be used when `TissueMAPS` is configured with ``use_spark=true``):

    .. code-block:: ini

        [setup/yarn]
        provider=ansible
        yarn_manager_groups=hadoop_master,ganlia_monitor
        yarn_worker_groups=hadoop_worker,ganlia_monitor
        global_var_cluster_name=yarn
        global_var_cluster_owner=XXX
        global_var_cluster_location=XXX

        [cluster/yarn]
        cloud=sciencecloud
        login=ubuntu
        setup_provider=yarn
        ssh_to=master
        yarn_manager_nodes=1
        yarn_worker_nodes=4
        security_group=XXX
        network_ids=XXX
        image_id=XXX

        [cluster/yarn/yarn_manager]
        flavor=XXX

        [cluster/yarn/yarn_worker]
        flavor=XXX


Now that the indivdual cluster components of the `TissueMAPS` grid are built, we "wire" them all together and set up the `Ganglia` server to monitor the different clusters. The local machine will host this server. To this end, add the ``ganglia_server`` group to the customized `Ansible` inventory file ``/etc/ansible/hosts``. We further add the abstract ``tissuemaps_compute`` group that combines all "slurm" hosts into one group:

.. code-block:: ini

    [ganglia_server]
    localhost ansible_connection=local

    [tissuemaps_compute:children]
    slurm_master
    slurm_workers

    [tissuemaps_compute:vars]
    yarn_master_ssh_host=XXX

To facilitate configuration of the ``ganglia_server`` `group`, set the required variables in a dedicated group-specific file ``/etc/ansible/group_vars/ganglia_server``. We need to tell the `ganglia` server, which "data sources" it should monitor. To this end, we need to specify the `name` of each ``cluster`` and the `addresses` of the corresponding `hosts`. This information can be found in the `Ansible` inventory file ``???`` created by `elasticluster` based on the above configuration.

.. cdoe-block:: yaml

    grid_name: TissueMAPS
    clusters:
        - name: slurm
          hosts:
            - XXX  # frontend001
            - XXX  # slurm_worker001
            ...    # slurm_worker[n]
        - name: postgresql
          hosts:
            - XXX  # postgresql_server001
        - name: glusterfs
          hosts:
            - XXX  # glusterfs_server001
            ...    # glusterfs_server[n]
        - name: yarn
          hosts:
            - XXX  # yarn_manager001
            - XXX  # yarn_worker001
            ...    # yarn_worker[n]

After providing the information for the different cluster components, run the "ganglia" playbook provided by `elasticluster` to setup the monitoring server::

    ansible-playbook  ~/elasticluster/share/playbooks/ganglia.yml


Finally, apply an additional post-configuration step to all `hosts` of the created `TissueMAPS` grid that ensures that the different components can communicate with each other::

    ansible-playbook  ~/tmsetup/playbooks/grid.yml

