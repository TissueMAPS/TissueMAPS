
************
Installation
************

`TissueMAPS` uses a client-server model:

* **Client** code runs on local machines and interacts with the server over `HTTP <https://en.wikipedia.org/wiki/Hypertext_Transfer_Protocol>`_ protocol. No local installation is required for the user interface, since the `Javascript` code is served to users via the browser. Other client implementations (active programming and command line interfaces) need to be installed locally. They have very few dependencies and are easy to install on various platforms (Linux, MacOSX, Windows).

* **Server** code can also run on a local machine, but is typically deployed on a remote machine (or multiple machines). It has many dependencies, is more complicated to setup and is designed for `UNIX <http://www.unix.org/what_is_unix.html>`_ plaforms (we have never tested it, but the server probably won't run on Windows). This section provides instructions for manual setup on MacOSX and Linux Ubuntu. `TissuMAPS` further provides automated configuration management and deployment routines for `Ubuntu 14.04 <http://releases.ubuntu.com/14.04/>`_ in form of `Ansible playbooks <http://docs.ansible.com/ansible/playbooks.html>`_. For more information, please refer to the :doc:`cloud setup and deployment <setup_and_deployment>`

.. _clients:

Clients
=======

Users can interact with the program via a standard web browser (tested with `Chrome <https://www.google.com/chrome/>`_, `Firefox <https://www.mozilla.org/en-US/firefox/new/>`_ and `Safari <http://www.apple.com/safari/>`_) without the need to install any additional software locally.

Other client implementations are available in various languages through the `TmClient <https://github.com/TissueMAPS/TmClient>`_ repository.

.. _python-client:

Python client
-------------

The `tmclient` Python package provides an active programming and command line interface for uploading or downloading data.


Requirements
^^^^^^^^^^^^

* `Python <https://www.python.org/>`_ (version 2.7): Many platforms are shipped with Python already pre-installed. If not, it can downloaded from `python.org <https://www.python.org/downloads/>`_. We recommend using version 2.7.9 or higher.
* `Pip <https://pip.pypa.io/en/stable/>`_: The Python package manager is automatically installed with Python distributions downloaded from python.org. Otherwise, it can be installed with the `get-pip.py <https://bootstrap.pypa.io/get-pip.py>`_ script.
* `Git <https://git-scm.com/>`_: Available on Linux and MaxOSX via various package managers. On Windows, we recommend using `Git Bash <https://git-for-windows.github.io/>`_.
* `OpenCV <http://opencv.org/>`_ (version 3.1): Prebuild binaries for different platforms are available for download on `opencv.org <http://opencv.org/downloads.html>`_. Detailed instructions for building the latest version from source can be found in the `online documentation <http://docs.opencv.org/3.1.0/df/d65/tutorial_table_of_content_introduction.html>`_. Packages are also available via `homebrew <https://github.com/Homebrew/homebrew-science/blob/master/opencv3.rb>`_ on `MacOSX` or cross-platform via `anaconda <https://anaconda.org/menpo/opencv3>`_. Note that when using a virtual environment, the Python bindings need to be  manually copied or linkied, since the package gets installed globally.


Installation
^^^^^^^^^^^^

The `tmclient` package can be installed via `pip`::

    pip install git+https://github.com/tissuemaps/tmclient.git


.. _matlab-client:

Matlab client
-------------

Requirements
^^^^^^^^^^^^

* `Matlab <https://mathworks.com/products/matlab/>`_ (version 2014b or later): Requires `RESTful web services <https://ch.mathworks.com/help/matlab/internet-file-access.html>`_, which were introduced in version 2014b.


Installation
^^^^^^^^^^^^

To be able to import the `tmclient` Matlab package, the source code needs to be downloaded from Github.
To this end, clone the `TmClient <https://github.com/TissueMAPS/TmClient>`_ repository using the `git` command line interface on Linux/MacOSX or `Git Bash <https://git-for-windows.github.io/>`_ on Windows::

    git clone https://github.com/TissueMAPS/TmClient.git $HOME/tmclient

The path to the local copy of the Matlab code needs to be added to the Matlab search path, by either using a ``startup.m`` file or setting the ``MATLABPATH`` environment variable. For further information please refer to the `Matlab online documentation <https://mathworks.com/help/matlab/matlab_env/add-folders-to-matlab-search-path-at-startup.html>`_.


.. _r-client:

R client
--------

Requirements
^^^^^^^^^^^^

* `R <https://www.r-project.org/>`_ (version 3.0.2 or higher): R is available for `download <https://cran.r-project.org/mirrors.html>`_.
* `devtools <https://cran.r-project.org/web/packages/devtools/README.html>`_: The package can be installed via `CRAN <https://cran.r-project.org/>`_: ``install.packages("devtools")``.


Installation
^^^^^^^^^^^^

The `tmclient` R package can be installed from the R console using the `devtools` package:

.. code:: R

    library(devtools)
    install_github("TissueMAPS/TmClient")

.. _server:

Server
======

The server backend is designed for `UNIX`-based operating systems. It has been successfully deployed in production on `Ubuntu 14.04 Trusty <http://releases.ubuntu.com/14.04/>`_ and development on `MacOSX 10.10.5 Yosemite <https://support.apple.com/kb/DL1833?locale=en_US>`_.

For MacOSX we highly recommend using the `Homebrew <http://brew.sh/>`_ package manager.

The `TissueMAPS` server is comprised of different components: web, storage, and compute units. These components might be all installed on the same machine or distributed accross multiple machines, depending on available resources and expected workloads.

Below, the individual server components are desribed and instructions for manual installation and configuration instructions are provided for setup on a single machine. The manual installation guide gives an overview of the different components and their requirements and can be helpful for setting up a `TissueMAPS` server for local development. Note that you don't need to install web and application servers for local debugging and testing, since development servers are provided through the `TmUI <https://github.com/TissueMAPS/TmUI>`_ and `TmServer <https://github.com/TissueMAPS/TmServer>`_ repositories, respectively. For production deployment, please refer to the `cloud setup and deployment <setup_and_deployment>`_ section, where you'll find instructions on how to setup `TissueMAPS` in the cloud in a fully automated and reproducible way.

.. _web-server:

Web server
----------

The `TmUI <https://github.com/TissueMAPS/TmUI>`_ repository hosts the code for the `AngularJS <https://angularjs.org/>`_ web app. It is written to large extends in `TypeScript <https://www.typescriptlang.org/>`_ and managed by `Gulp <http://gulpjs.com/>`_.
The `HTTP` server serves the app (`HTML <http://www.w3schools.com/html/html_intro.asp>`_ templates and built `Javascript <http://www.w3schools.com/js/js_intro.asp>`_ code) to clients.

.. _web-server-requirements:

Requirements
^^^^^^^^^^^^

* `NodeJs <https://nodejs.org/en/>`_ and its package manager `npm <https://www.npmjs.com/>`_:

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

* `NGINX <https://www.nginx.com/>`_ (only required for production deployment):

    On Ubuntu::

        sudo apt-get -y install nginx

    On MacOSX::

        brew install nginx

.. _web-server-installation:

Installation
^^^^^^^^^^^^

Clone the `TmUI <https://github.com/TissueMAPS/TmUI>`_ repository (including submodules) from Github and cd into the created directory::

    git clone --recursive https://github.com/TissueMAPS/TmUI.git ~/tmclient
    cd ~/tmui/src

Install `node` packages (globally)::

    npm install -g

Install `bower <https://bower.io/>`_ packages::

    bower install

Build cliet code for production deployment::

    gulp build --production

This will create a ``build`` subdirectory. The contents of this directory can now be served by a HTTP web server, such as `NGINX`.

.. _web-server-configuration:

Configuration
^^^^^^^^^^^^^

When using `NGINX`, create an application-specific site and set the path to the ``build`` directory in ``/etc/nginx/sites-available/tissuemaps``::

    server {
        listen 80;

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

Enable the ``tissuemaps`` site by creating the following softlink::

    sudo ln -s /etc/nginx/sites-available/tissuemaps /etc/nginx/sites-enabled/tissuemaps

Set the following application-specific parameters in ``/etc/nginx/conf.d/tissuemaps.conf`` (the values may need to be adapated for your use case)::

    uwsgi_read_timeout 3600;
    uwsgi_buffering off;
    client_max_body_size 10000M;


.. _application-server:

Application server
------------------

The application server communicates between the web server and the Python web application, using the `Web Server Gateway Interface (WSGI) specification <https://wsgi.readthedocs.io/en/latest/>`_.
Since we will run web and application servers on the same machine, we use a Unix socket, which communicates with the web proxy server via the `WSGI` protocol instead of a network port. This would need to be changed when the different server components operate on separate machines.

.. _application-server-requirements:

Requirements
^^^^^^^^^^^^

* `Python <https://www.python.org/>`_ (version 2.7): Ubuntu (up to version 14.04) and MacOSX come with Python included. However, installing a newer version (2.7.9 or higher) is recommended. On MacOSX make sure you use the version installed via `Homebrew`!
* `Pip <https://pip.pypa.io/en/stable/>`_: The Python package manager is typically already installed with the Python distributions, but we need to update it to make sure we use the most recent version.

    On Ubuntu::

        sudo add-apt-repository ppa:fkrull/deadsnakes-python2.7
        sudo apt-get update
        sudo apt-get -y install python2.7

        sudo apt-get -y install python-pip python-dev build-essential
        sudo pip install --upgrade pip
        sudo pip install --upgrade setuptools

    On MacOSX::

        brew install python
        sudo pip install --upgrade pip
        sudo pip install --upgrade setuptools

.. _application-server-installation:

Installation
^^^^^^^^^^^^

`uWSGI` can be installed via the Python package manager `pip`::

    sudo pip install uwsgi


If you don't install the application on a dedicated machine, we recommend using a Python virtual environment.

To this end, install `virtualenv <https://virtualenv.readthedocs.org/en/latest/>`_ and `virtualenvwrapper <https://virtualenvwrapper.readthedocs.org/en/latest/>`_::

    sudo pip install virtualenv virtualenvwrapper

Add the following lines to your ``~/.bash_profile`` file:

.. code-block:: bash

    export WORKON_HOME=$HOME/.virtualenvs
    source /usr/local/bin/virtualenvwrapper.sh

Then create a ``tissuemaps`` project for all `TissueMAPS` dependencies::

    mkvirtualenv tissuemaps

You can later activate the environment as follows::

    workon tissuemaps

.. warning::

    A coexisting `anaconda <http://docs.continuum.io/anaconda/pkg-docs>`_ installation doens't play nice with virtual environments and will create problems; see `potential solution <https://gist.github.com/mangecoeur/5161488>`_. It might also create issues with Python bindings installed by other package managers. For this reason (and others) we prefer working with good old virtualenvs.


Configuration
^^^^^^^^^^^^^

Create a direcotory for `TissueMAPS`-specific configurations::

    mkdir ~/.tmaps

and configure `uWSGI` in ``~/.tmaps/uwsgi.ini``:

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

Ensure that the server runs in `gevent <http://www.gevent.org/>`_ mode and
adapt configurations according to available computational resources.

When working with a virtual environment (as described above), include the path to the project in the configuration file:

.. code-block:: ini

    home = $(VIRTUALENVWRAPPER_HOOK_DIR)/tissuemaps

Create a upstart script in ``~/.tmaps/uwsgi.sh``:

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

The actual `TissueMAPS` Python web application is implemented in the `Flask <http://flask.pocoo.org/>`_ micro-framework.

.. _application-requirements:

Requirements
^^^^^^^^^^^^

* `PostgreSQL <http://postgresxl.org/>`_ (version 9.6): `PostgreSQL` is available on Ubuntu by default, but we want a more recent version with improved performanced. On MacOSX `PostgreSQL` is avaible via `homebrew`, but the `PostgresApp <http://postgresapp.com/>`_ is a convenient alternative.

    On Ubuntu::

        sudo sh -c "echo 'deb http://apt.postgresql.org/pub/repos/apt/ trusty-pgdg main' > /etc/apt/sources.list.d/pgdg.list"

        wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -
        sudo apt-get update

        sudo apt-get -y install postgresql-9.6
        sudo apt-get -y install postgresql-9.6-postgis-2.2 postgresql-9.6-postgis-scripts postgresql-contrib-9.6 postgresql-server-dev-all postgresql-client

        sudo apt-get -y install python-psycopg2

    On MacOSX::

        brew tap petere/postgresql
        brew install postgresql-9.6 && brew link -f postgresql-9.6

        # Postgis extension
        brew install pex
        brew install gettext && brew link -f gettext
        pex init
        pex -g /usr/local/opt/postgresql-9.6 install postgis

* `OpenCV <`http://opencv.org/>`_ (version 3.1):

    On Ubuntu the `apt-get` package manager currently only provides version 2.4. Version 3.1 needs to be `build from source <http://docs.opencv.org/3.1.0/d7/d9f/tutorial_linux_install.html>`_::

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

    This will build `OpenCV` globally. If you work with a virtual enviroment, create a softlink for the Python bindings (exemplified for ``tissuemaps`` project):

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

* `Spark <http://spark.apache.org/>`_ (version 2.0): Requires installation with support for `YARN <http://hadoop.apache.org/docs/stable/hadoop-yarn/hadoop-yarn-site/YARN.html>`_ for running Spark on a cluster as well as `Hive <https://hive.apache.org/>`_ and `JDBC <http://docs.oracle.com/javase/tutorial/jdbc/overview/index.html>`_ for `Spark SQL <http://spark.apache.org/docs/latest/sql-programming-guide.html#overview>`_ integration. It is important to `build <http://spark.apache.org/docs/latest/building-spark.html#specifying-the-hadoop-version>`_ Spark againgst the `HDFS <http://hadoop.apache.org/docs/r1.2.1/hdfs_design.html>`_ version available in your cluster environment, since `HDFS` is not compatible across versions. Pyspark further requires the same minor version of Python in both drivers and workers.

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

.. _application-installation:

Installation
^^^^^^^^^^^^

Download the server code from Github::

    git clone https://github.com/TissueMAPS/TmServer.git ~/tmserver

Install the `tmserver` Python package via `pip`::

    cd ~/tmserver && pip install -e . --user

This will install the package in `editable mode <https://pip.pypa.io/en/stable/reference/pip_install/#editable-installs>`_, which allows you to modify code locally without having to reinstall the package.

.. _application-configuration:

Configuration
^^^^^^^^^^^^^

.. _application-configuration-postgresql:

PostgreSQL
++++++++++

Create a `database cluster <https://www.postgresql.org/docs/current/static/creating-cluster.html>`_ using the default ``data_directory`` and start the server (here demonstrated for `PostgreSQL` version 9.6). These steps might have already been performed automatically upon installation:

    On Ubuntu (as ``postgres`` user)::

        sudo su - postgres
        /usr/lib/postgresql/9.6/bin/initdb -D /var/lib/postgresql/9.6/main
        /usr/lib/postgresql/9.6/bin/pg_ctl -D /var/lib/postgresql/9.6/main -l logfile restart

    On MacOsX (as current user)::

        /usr/local/opt/postgresql-9.6/bin/initdb -D /usr/local/var/lib/postgresql/9.6/main
        /usr/local/opt/postgresql-9.6/bin/pg_ctrl -D /usr/local/var/lib/postgresql/9.6/main -l logfile restart

On MacOSX you may want to add the `PostgreSQL` executables to the ``$PATH`` in your ``~/.bash_profile`` file:

.. code-block:: bash

        export PATH=$PATH:/usr/local/opt/postgresql-9.6/bin
        export MANPATH=$MANPATH:/usr/local/opt/postgresql-9.6/share/man

On Ubuntu ``service`` can also be used to start and stop the database server::

        sudo service postgresql restart

Configure postgres in ``/etc/postgresql/9.6/main/postgresql.conf``:

.. code-block:: sql

    listen_addresses = '*'
    host  all  all  .0.0.0/0  md5

Now enter `psql` console:

    On Ubuntu (as ``postgres`` user)::

        sudo -u postgres psql postgres

    On MacOSX (as current user)::

        psql postgres

to change permissions for the postgres user (it may already exist) and set a new password:

.. code-block:: sql

    CREATE USER postgres;
    ALTER USER postgres WITH SUPERUSER;
    ALTER USER postgres WITH PASSWORD 'XXX';

Then create the ``tissuemaps`` database:

.. code-block:: sql

    CREATE DATABASE tissuemaps;

and the `postgis <http://www.postgis.net/>`_ extension:

.. code-block:: sql

    CREATE EXTENSION postgis;

Now, you should be able to connect to the database as ``postgres`` user with your new password::

    psql -h localhost tissuemaps postgres

It's convenient to use a `pgpass file <https://www.postgresql.org/docs/current/static/libpq-pgpass.html>`_ to be able to connect to the database without having to type the password every time::

    echo "*:5432:tissuemaps:postgres:XXX" > ~/.pgpass
    chmod 0600 ~/.pgpass

When using a mounted filesystem for data storage, you can create a symlink to ``data_dirctory`` or use an alternative directory. Make sure, however, to set the correct permissions for the parent directory of the desired data directory. For more information please refer to the PostgreSQL online documentation on `file locations <https://www.postgresql.org/docs/current/static/runtime-config-file-locations.html>`_ and `creation of a new database cluster <https://www.postgresql.org/docs/9.6/static/app-initdb.html>`_.

.. _application-configuration-tissuemaps:

TissueMAPS
++++++++++

Create a `TissueMAPS` configuration file ``~/.tmaps/tissuemaps.cfg`` and set the ``db_password`` parameter (replace ``XXX`` with the actual password you defined above):

.. code-block:: ini

    [DEFAULT]
    db_password = XXX

Additional parameters can be set. Please refer to :doc:`tmlib.config.Setup <tmlib.config>`.

Finally, populate the ``tissuemaps`` database with the tables defined in the :doc:`tmlib.models` package. To this, call the following utility script::

    tm_create_tables


.. _application-configuration-gc3pie:

GC3Pie
++++++

Under the hood, `TissueMAPS` uses `GC3Pie <http://gc3pie.readthedocs.io/en/latest/programmers/index.html>`_ for computational job management. The program provides a high-level API around different cluster backends (and localhost).

Create a configuration file ``~/.gc3/gc3pie.conf`` and modify it according to your computational infrastructure. For more information please refer to the `GC3Pie online documentation <http://gc3pie.readthedocs.org/en/latest/users/configuration.html>`_:

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

.. tip:: If you are not sure about your architecture, setting ``override=yes`` usually does the trick.

.. _startup:

Startup
-------

Now that all parts are installed and configured, the servers can be started.

.. _startup-production:

Production mode
^^^^^^^^^^^^^^^

For production web server (`NGINX`) and application server (`uWSGI`) need to be started:

On Ubuntu::

    sudo service nginx start
    sudo service uwsgi start

.. _development-production:

Development mode
^^^^^^^^^^^^^^^^

For local developement and testing `NGINX` and `uWSGI` are not required.

The `tmserver` package provides a command line tool that starts a `development application server <http://flask.pocoo.org/docs/0.11/server/#server>`_::

    tm_server

The client installation also provides a `development web server <https://www.npmjs.com/package/gulp-webserver>`_ to dynamically build client code with live reload functionality::

    cd ~/tmui/src
    gulp

This will automatically start the server on localhost (port 8002). To access the website, point your browser to ``http://localhost:8002/``.

Both dev servers provide live reload functionality. They will auto-watch files and rebuild code upon changes, which is useful for local development and testing.

