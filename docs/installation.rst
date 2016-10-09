.. _installation:

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

.. _installation:

Installation
^^^^^^^^^^^^

The `tmlib` Python package can be installed via `pip`::

    pip install git+https://github.com/TissueMAPS/TmClient.git


.. _matlab-client:

Matlab client
-------------

.. _requirements:

Requirements
^^^^^^^^^^^^

* `Matlab <https://mathworks.com/products/matlab/>`_ (version 2014b or later): Requires `RESTful web services <https://ch.mathworks.com/help/matlab/internet-file-access.html>`_, which were introduced in version 2014b.


.. _installation:

Installation
^^^^^^^^^^^^

To be able to import the `tmclient` Matlab package, the source code needs to be downloaded from Github.
To this end, clone the `TmClient <https://github.com/TissueMAPS/TmClient>`_ repository using the `git <https://git-scm.com/>`_ command line interface on Linux/MacOSX or `Git Bash <https://git-for-windows.github.io/>`_ on Windows::

    git clone https://github.com/TissueMAPS/TmClient.git $HOME/tmclient

The path to the local copy of the Matlab code needs to be added to the Matlab search path, by either using a ``startup.m`` file or setting the ``MATLABPATH`` environment variable. For further information please refer to the `Matlab online documentation <https://mathworks.com/help/matlab/matlab_env/add-folders-to-matlab-search-path-at-startup.html>`_.


.. _r-client:

R client
--------

.. _requirements:

Requirements
^^^^^^^^^^^^

* `R <https://www.r-project.org/>`_ (version 3.0.2 or higher): R is available for `download <https://cran.r-project.org/mirrors.html>`_.
* `devtools <https://cran.r-project.org/web/packages/devtools/README.html>`_: The R package can be downloaded from CRAN: ``install.packages("devtools")``.

.. _installation:

Installation
^^^^^^^^^^^^

The `tmclient` R package can be installed via the R console using the `devtools` package:

.. code:: R

    library(devtools)
    install_github("TissueMAPS/TmClient")

.. _server:

Server
======

The server backend is designed for `UNIX`-based operating systems. It has been successfully deployed in production on `Ubuntu 14.04 Trusty <http://releases.ubuntu.com/14.04/>`_ and used for development on `MacOSX 10.10.5 Yosemite <https://support.apple.com/kb/DL1833?locale=en_US>`_.

The different servers might be all installed on the same machine or on different VMs, depending on available resources and expected workloads. For simplicity, installation instructions are given for use on `localhost`.

.. _web-server:

Web server
----------

The `TmClient <https://github.com/TissueMAPS/TmClient/tree/master/src/javascript>`_ repository hosts the code for the `AngularJS <https://angularjs.org/>`_ app. It is written to large extends in `TypeScript <https://www.typescriptlang.org/>`_ and managed by `Gulp <http://gulpjs.com/>`_.
The `HTTP` server serves the app (`HTML <http://www.w3schools.com/html/html_intro.asp>`_ templates and built `Javascript <http://www.w3schools.com/js/js_intro.asp>`_ code) to clients.

.. _requirements:

Requirements
^^^^^^^^^^^^

* `node <https://nodejs.org/en/>`_: It is available for `download <https://www.npmjs.com/package/npm>`_ and can alternatively be installed with various `package managers <https://nodejs.org/en/download/package-manager/>`_.
* `npm <https://www.npmjs.com/>`_: Npm already comes with Node, but can be installed in `facier ways <https://www.npmjs.com/package/npm>`_ if desired.

On Ubuntu::

    curl -sL https://deb.nodesource.com/setup_6.x | sudo -E bash -
    sudo apt-get install nodejs

On MacOSX::

    brew install node

* `NGINX <https://www.nginx.com/>`_ (for production deployment): `Pre-build packages <http://nginx.org/en/docs/install.html>`_ are available for Linux.

On Ubuntu::

    sudo apt-get install nginx

On MacOSX::

    brew install nginx

.. _installation:

Installation
^^^^^^^^^^^^

Clone the `TmClient <https://github.com/TissueMAPS/TmClient>`_ repository (including submodules) from Github and change the current directory::

    git clone --recursive https://github.com/TissueMAPS/TmClient.git $HOME/tmclient
    cd $HOME/tmclient/src/javascript

Install `node` packages::

    npm install

Install `bower <https://bower.io/>`_ packages::

    node_modules/bower/bin/bower install

Build cliet code for production deployment::

    node_modules/gulp/bin/gulp.js build --production

This will create a ``build`` subdirectory. The contents of this directory can now be served by a separate HTTP web server, such as `NGINX`.

.. _configuration:

Configuration
^^^^^^^^^^^^^

When using `NGINX`, create an application-specific site and set the path to the ``build`` directory in ``/etc/nginx/site-available/tissuemaps``::

    server {
        listen 80;
        server_name localhost;

        access_log /var/log/nginx/tissuemaps-access.log;
        error_log /var/log/nginx/tissuemaps-error.log;

        # all non-api requests are file requests and should be served
        # from the built client dir
        root /home/ubuntu/tmclient/src/javascript/build;
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

and enable the site by creating the following softlink::

    sudo ln -s /etc/nginx/sites-available/tissuemaps /etc/nginx/sites-enabled/tissuemaps

Also set the following application-specific parameters in ``/etc/nginx/conf.d/tissuemaps.conf``::

    uwsgi_read_timeout 3600;
    uwsgi_buffering off;
    client_max_body_size 10000M;


.. _web-application-server:

Web application server
----------------------

The application server communicates between the web server and the Python web application, using the `Web Server Gateway Interface (WSGI) specification <https://wsgi.readthedocs.io/en/latest/>`_.
Here we use a Unix socket, which uses the with `WSGI` protocol, instead of a network port for communication with the `NGINX` proxy server. This works when all of the components are operating on a single machine, but needs to be changed for a multi-VM configuration.

.. _requirements:

Requirements
^^^^^^^^^^^^

* `Python <https://www.python.org/>`_ (version 2.7): Ubuntu (up to version 14.04) and MacOSX come with Python included. However, installing a newer version (2.7.9 or higher) is recommended. For compatibility, all machines should have the same Python version installed!
* `Pip <https://pip.pypa.io/en/stable/>`_: The Python package manager is typically already installed with the Python distributions.

    On Ubuntu::

        sudo add-apt-repository ppa:fkrull/deadsnakes-python2.7
        sudo apt-get update
        sudo apt-get install python2.7

        sudo apt-get install python-pip python-dev build-essential
        sudo pip install --upgrade pip

    On MacOSX::

        brew install python

* `Git <https://git-scm.com/>`_:

    On Ubuntu::

        sudo apt-get git

    On MacOSX::

        brew install git

.. _installation:

Installation
^^^^^^^^^^^^

If you don't install the application on a dedicated machine, we recommend using a virtual environment.

To this end, install `virtualenv <https://virtualenv.readthedocs.org/en/latest/>`_ and `virtualenvwrapper <https://virtualenvwrapper.readthedocs.org/en/latest/>`_ and set up your environment::

    sudo pip install virtualenv
    sudo pip install virtualenvwrapper

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

On MacOSX it can also be installed via homebrew, which can then be conviently controlled via `services <https://github.com/Homebrew/homebrew-services>`::

    brew install uwsgi

.. _configuration:

Configuration
^^^^^^^^^^^^^

Download the server code from Github::

    git clone https://github.com/TissueMAPS/TmServer.git $HOME/tmserver

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
    vaccum = true

    master = true
    plugins = python
    processes = 16
    gevent = 100

    for-readline = $(HOME)/.tmaps/env.txt
      env = %(_)
    endfor =

Ensure that it runs in `gevent <http://www.gevent.org/>`_ mode and
adapt configurations according on available computational resources.

When working with a virtual environment, include the path to the project:

.. code-block:: ini

    home = $(VIRTUALENVWRAPPER_HOOK_DIR)/tissuemaps

To make environment variables available to the application, capture the environment and store it in the file ``$HOME/.tmaps/environment.txt``::

    env > $HOME/.tmaps/env.txt

Don't forget to update the file when changing environment variables later on!

Then create an upstart script in ``$HOME/.tmaps/uwsgi.sh``:

.. code-block:: bash

    #!/bin/bash
    uwsgi --ini $HOME/.tmaps/uwsgi.ini

and set the path to the script in the service definition file ``/etc/init/uwsgi.conf`` (exemplified here for ``ubuntu`` user)::

    description "uWSGI server instance configured to serve TissueMAPS"

    start on runlevel [2345]
    stop on runlevel [!2345]

    setuid ubuntu
    setgid ubuntu

    chdir /home/ubuntu/.tmaps
    exec bash uwsgi.sh

.. _web-application:

Web application
---------------

The actual Python web application is implemented in the `Flask <http://flask.pocoo.org/>`_ micro-framework.


.. _requirements:

Requirements
^^^^^^^^^^^^

* `PostgreSQL <http://postgresxl.org/>`_ (version 9.6): PostgreSQL is available on Ubuntu by default, but we want a more recent version with improved performanced.

    An apt repository is available for `download <https://www.postgresql.org/download/linux/ubuntu/>`_ on Ubuntu::

        sudo sh -c "echo 'deb http://apt.postgresql.org/pub/repos/apt/ trusty-pgdg main' > /etc/apt/sources.list.d/pgdg.list"

        wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -
        sudo apt-get update

        sudo apt-get install postgresql-9.6
        sudo apt-get install postgresql-9.6-postgis-2.2 postgresql-9.6-postgis-scripts postgresql-contrib-9.6 postgresql-server-dev-all postgresql-client

        sudo apt-get install python-psycopg2

    On MacOSX::

        brew tap petere/postgresql
        brew install postgresql-9.6
        brew link -f postgresql-9.6
        echo "export PATH=$PATH:/usr/local/opt/postgresql-9.6/bin" >> $HOME/.bash_profile
        echo "export MANPATH=$MANPATH:/usr/local/opt/postgresql-9.6/share/man" >> $HOME/.bash_profile
        brew install pex
        pex init
        pex -g /usr/local/opt/postgresql-9.6 install postgis

    or just use the `PostgresApp <http://postgresapp.com/>`_.

* `OpenCV <`http://opencv.org/>`_ (version 3.1):

    On Ubuntu the `apt-get` package manager only provides version 2.4. Version 3.1 needs to be `build from source <http://docs.opencv.org/3.1.0/d7/d9f/tutorial_linux_install.html>`_::

        git clone https://github.com/Itseez/opencv.git $HOME/opencv_source
        cd $HOME/opencv_source
        mkdir build
        cd build

        deactivate
        sudo pip install numpy

        sudo apt-get install cmake
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

        sudo apt-get install libhdf5-dev hdf5-tools

    On MacOSX::

        brew tab homebrew/science
        brew install hdf5

* `Bio-Formats command line tools <http://www.openmicroscopy.org/site/support/bio-formats5.2/users/comlinetools/>`_ (version 5.1 or higher):

    On Ubuntu::

        sudo apt-get install openjdk-7-jdk
        sudo apt-get install unzip
        curl -s -o $HOME/bftools.zip https://downloads.openmicroscopy.org/bio-formats/5.2.3/artifacts/bftools.zip
        unzip bftools.zip

    On MacOSX::

        brew tab ome/alt
        brew install bioformats51

* `Spark <http://spark.apache.org/>`_ (version 2.0): Requires installation with support for `YARN <http://hadoop.apache.org/docs/stable/hadoop-yarn/hadoop-yarn-site/YARN.html<Paste>>`_ for running Spark on a cluster as well as `Hive <https://hive.apache.org/>`_ and `JDBC <http://docs.oracle.com/javase/tutorial/jdbc/overview/index.html>`_ for `Spark SQL <http://spark.apache.org/docs/latest/sql-programming-guide.html#overview>`_ integration. It is important to `build <http://spark.apache.org/docs/latest/building-spark.html#specifying-the-hadoop-version>`_ Spark againgst the `HDFS <http://hadoop.apache.org/docs/r1.2.1/hdfs_design.html>`_ version available in your cluster environment, since `HDFS` is not cross compatible across versions. Pyspark further requires the same minor version of Python in both drivers and workers.

    On Ubuntu::

        sudo wget http://d3kbcqa49mib13.cloudfront.net/spark-2.0.1.tgz
        tar -xvzf spark-2.0.1.tgz && mv spark-2.0.1 spark
        cd spark
        sudo apt-get update

        sudo apt-get install openjdk-7-jdk
        export JAVA_HOME=/usr/lib/jvm/java-1.7.0-openjdk-amd64

        sudo apt-get install maven
        export MAVEN_OPTS="-Xmx2g -XX:MaxPermSize=512M -XX:ReservedCodeCacheSize=512m"
        ./build/mvn -Pyarn -Phadoop-2.7 -Dhadoop.version=2.7.1 -Phive -Phive-thriftserver -DskipTests clean package

        echo "export PATH=$PATH:$HOME/spark/bin" >> $HOME/.bash_profile

    On MacOSX::

        brew install apache-spark

* `lxml <http://lxml.de/>`_:

    On Ubuntu::

        sudo apt-get install python-lxml

    The package is not installable via `pip` on Ubuntu. When using a virtual environment, the globally installed package must be linked::

        cd $VIRTUALENVWRAPPER_HOOK_DIR/tissuemaps/lib/python2.7/site-packages
        ln -s /usr/lib/python2.7/dist-packages/lxml lxml

    On MacOSX::

        pip install lxml

.. _installation:

Installation
^^^^^^^^^^^^

Install the `tmserver` Python package via `pip`::

    cd $HOME/tmserver
    pip install .

You may want to install `TissueMAPS` packages in developer mode to be able to modify code locally. To this end, you can clone and install repositories in ``$HOME/tmserver/requirements/requirements-git.txt`` manually.

.. _configuration:

Configuration
^^^^^^^^^^^^^

PostgreSQL
~~~~~~~~~~

Create a database cluster for a given ``data_directory`` and start the server (here demonstrated for the default ``data_directory`` - it might have already been done automatically upon installation):

    On Ubuntu (as ``postgres`` user)::

        sudo su - postgres
        /usr/lib/postgresql/9.6/bin/initdb -D /var/lib/postgresql/9.6/main
        /usr/lib/postgresql/9.6/bin/pg_ctl -l logfile restart

    On MacOsX (as current user):

    With `Homebrew` installation::

        initdb -D /usr/local/var/lib/postgresql/9.6/main
        pg_ctrl -D /usr/local/var/lib/postgresql/9.6/main -l logfile restart

    With `PostgresApp` installation - or just double-click the application icon::

        initdb -D $HOME/Library/Application\ Support/Postgres/var-9.6
        pg_ctl -D $HOME/Library/Application\ Support/Postgres/var-9.6 -l logfile restart

On Ubuntu ``service`` can also be used to start and stop the database server::

        sudo service postgresql restart

Configure postgres in ``/etc/postgresql/9.6/main/postgresql.conf``:

.. code-block:: sql

    listen_addresses = '*'
    host  all  all  .0.0.0/0  md5

Enter `psql` console:

    On Ubuntu (as ``postgres`` user)::

        sudo -u postgres psql postgres

    On MacOsX (as current user)::

        psql postgres

and change password for ``postgres`` user:

.. code-block:: sql

    CREATE USER postgres;
    ALTER USER postgres WITH PASSWORD 'XXX';

and create the ``tissuemaps`` database and `postgis <http://www.postgis.net/>`_ extension:

.. code-block:: sql

    CREATE DATABASE tissuemaps;
    \connect tissuemaps;
    CREATE EXTENSION postgis;

Now, you should be able to connect to the database as postgres user with your new password::

    psql -h localhost tissuemaps postgres

It's convenient to use a `pgpass file <https://www.postgresql.org/docs/current/static/libpq-pgpass.html>`_ to be able to connect to the database without having to type the password::

    echo "*:5432:tissuemaps:postgres:XXX" > $HOME/.pgpass
    chmod 0600 $HOME/.pgpass

When using a mounted filesystem for data storage, you can create a symlink to ``data_dirctory`` or use an alternative directory. Make sure, however, to set the correct permissions for the parent directory of the desired data directory. For more information please refer to the PostgreSQL online documentation on `file locations <https://www.postgresql.org/docs/current/static/runtime-config-file-locations.html>`_ and `creation of a new database cluster <https://www.postgresql.org/docs/9.6/static/app-initdb.html>`_.

Apache Spark (optional)
~~~~~~~~~~~~~~~~~~~~~~~

In case you have access to a `YARN <http://hadoop.apache.org/docs/stable/hadoop-yarn/hadoop-yarn-site/YARN.html>`_ cluster, copy the configuration files to each machine to which a tool requests might be submitted and provide the path to the local copy of the files via the environment variable ``YARN_CONF_DIR``, e.g.::

    echo "export YARN_CONF_DIR=/etc/hadoop" >> $HOME/.bash_profile

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

.. _starting servers:

Starting servers
----------------

.. _production-mode:

Production mode
^^^^^^^^^^^^^^^

Now that all components are installed and configured, web and application servers can be started:

On Ubuntu::

    sudo service nginx start
    sudo service uwsgi start


.. _dev-mode:

Dev mode
^^^^^^^^

For local developement and testing `NGINX` and `uWSGI` are not required.

The `tmserver` package provides a `development server <http://flask.pocoo.org/docs/0.11/server/#server>`_. To start this dev application server, just type::

    tmserver

The client installation also provides a `development web server <https://www.npmjs.com/package/gulp-webserver>`_ to dynamically build client code with live reload functionality::

    cd $HOME/tmclient/src/javascript
    node_modules/gulp/bin/gulp.js

This will automatically start the dev web server on localhost (port 8002). It will auto-watch files and rebuild the code upon changes, which is useful for local developement and testing.
