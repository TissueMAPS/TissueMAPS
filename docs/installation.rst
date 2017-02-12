
************
Installation
************

`TissueMAPS` uses a client-server model:

* **Client** code runs on the user's local machine and interacts with the server over `HTTP <https://en.wikipedia.org/wiki/Hypertext_Transfer_Protocol>`_ protocol. No local installation is required for the web user interface, since the `Javascript` code is served to the user via the browser. Other client implementations (active programming and command line interfaces) need to be installed locally. They have very few dependencies and are easy to install on various platforms (Linux, MacOSX, Windows).

* **Server** code can also run on the local machine, but is typically deployed on a remote machine (or multiple machines). It has many dependencies and is designed for `UNIX <http://www.unix.org/what_is_unix.html>`_ plaforms. This section provides instructions for manual deployment on MacOSX and Linux Ubuntu. For production deployment, please refer to the :doc:`cloud setup and deployment <setup_and_deployment>` section.

.. _clients:

Clients
=======

Users can interact with the *TissueMAPS* via a standard web browser (tested with `Chrome <https://www.google.com/chrome/>`_, `Firefox <https://www.mozilla.org/en-US/firefox/new/>`_ and `Safari <http://www.apple.com/safari/>`_) without the need to install any additional software locally.

Other client implementations are available in various languages through the `TmClient <https://github.com/TissueMAPS/TmClient>`_ repository.

.. _python-client:

Python client
-------------

The `tmclient` Python package provides an active programming and command line interface for uploading or downloading data.


Requirements
^^^^^^^^^^^^

* `Python <https://www.python.org/>`_ (version 2.7): Many platforms are shipped with Python already pre-installed. If not, it can be downloaded from `python.org <https://www.python.org/downloads/>`_. We recommend using version 2.7.9 or higher.
* `Pip <https://pip.pypa.io/en/stable/>`_: The Python package manager is automatically installed with Python distributions downloaded from python.org. Otherwise, it can be installed with the `get-pip.py <https://bootstrap.pypa.io/get-pip.py>`_ script.
* `Git <https://git-scm.com/>`_: Available on Linux and MaxOSX via various package managers. On Windows, we recommend using `Git Bash <https://git-for-windows.github.io/>`_.


Installation
^^^^^^^^^^^^

The `tmclient` package can be installed via `pip`::

    pip install tmclient


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

    git clone https://github.com/tissuemaps/tmclient

The path to the local copy of the Matlab code needs to be added to the Matlab search path, by either using a ``startup.m`` file or setting the ``MATLABPATH`` environment variable. For further information, please refer to the `Matlab documentation <https://mathworks.com/help/matlab/matlab_env/add-folders-to-matlab-search-path-at-startup.html>`_.


.. _r-client:

R client
--------

Requirements
^^^^^^^^^^^^

* `R <https://www.r-project.org/>`_ (version 3.0.2 or higher): R is available for download form `CRAN <https://cran.r-project.org/mirrors.html>`_.
* `devtools <https://cran.r-project.org/web/packages/devtools/README.html>`_: The package can also be installed via *CRAN*: ``install.packages("devtools")``.


Installation
^^^^^^^^^^^^

The `tmclient` R package can be installed from the R console using the `devtools` package:

.. code:: R

    library(devtools)
    install_github("TissueMAPS/TmClient")

.. _server:

Server
======

The server backend is designed for `UNIX`-based operating systems. It has been tested on `Ubuntu 14.04 Trusty <http://releases.ubuntu.com/14.04/>`_ and `MacOSX 10.10.5 Yosemite <https://support.apple.com/kb/DL1833?locale=en_US>`_.

For MacOSX we highly recommend using the `Homebrew <http://brew.sh/>`_ package manager.

The `TissueMAPS` server is comprised of different components: web, storage, and compute units. These components can all installed on the same machine or distributed accross multiple machines, depending on available resources and expected workloads.

Below, the individual server components are desribed and instructions for manual installation and configuration instructions are provided for setup on a single machine. The manual installation guide gives an overview of the different components and their requirements and can be helpful for setting up a `TissueMAPS` server for local development. Note that you don't need to install web and application servers for local debugging and testing, since development servers are provided through the `TmUI <https://github.com/TissueMAPS/TmUI>`_ and `TmServer <https://github.com/TissueMAPS/TmServer>`_ repositories, respectively. For production deployment, please refer to the `cloud setup and deployment <setup_and_deployment>`_ section, where you'll find instructions on how to setup `TissueMAPS` in the cloud in a fully automated and reproducible way.

.. _web-server:

Web server
----------

The `TmUI <https://github.com/TissueMAPS/TmUI>`_ repository hosts the code for the `AngularJS <https://angularjs.org/>`_ web app. It is written to large extends in `TypeScript <https://www.typescriptlang.org/>`_ and managed by `Gulp <http://gulpjs.com/>`_.

The *HTTP* web server serves the `HTML <http://www.w3schools.com/html/html_intro.asp>`_ templates and built `Javascript <http://www.w3schools.com/js/js_intro.asp>`_ code to clients.

.. _web-server-requirements:

Requirements
^^^^^^^^^^^^

* `NodeJs <https://nodejs.org/en/>`_ and its package manager `npm <https://www.npmjs.com/>`_:

    On Ubuntu::

        curl -sL https://deb.nodesource.com/setup_6.x | sudo -E bash -
        sudo apt-get -y install nodejs
        sudo npm install npm -g

    On MacOSX::

        brew install node
        npm install npm -g

* `Git <https://git-scm.com/>`_:

    On Ubuntu::

        sudo apt-get -y install git

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

    git clone --recursive https://github.com/TissueMAPS/TmUI.git ~/tmui
    cd ~/tmui/src

Install `node` packages and add executables to the ``PATH``::

    npm install

Install `bower <https://bower.io/>`_ packages::

    bower install

Build cliet code for production deployment::

    gulp build --production

This will create a ``build`` subdirectory. The contents of this directory can now be served by a HTTP web server, such as `NGINX`.

.. _web-server-configuration:

Configuration
^^^^^^^^^^^^^

When using `NGINX`, create an application-specific site and set the path to the ``build`` directory in ``/etc/nginx/sites-available/tissuemaps`` (exemplified here for the ``ubuntu`` user):

.. code-block:: none

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

Remove the ``default`` site and enable the ``tissuemaps`` site by creating the following softlink::

    sudo rm /etc/nginx/sites-enabled/default
    sudo ln -s /etc/nginx/sites-available/tissuemaps /etc/nginx/sites-enabled/tissuemaps

Set the following application-specific parameters in ``/etc/nginx/conf.d/tissuemaps.conf`` (the values may need to be adapated for your use case):

.. code-block:: none

    uwsgi_read_timeout 3600;
    uwsgi_buffering off;
    client_max_body_size 10000M;

.. note:: You can of course use an alternative web server, such as `Apache <https://httpd.apache.org/>`_.


.. _application-server:

Application server
------------------

The application server communicates between the web server and the Python web application, using the `Web Server Gateway Interface (WSGI) specification <https://wsgi.readthedocs.io/en/latest/>`_.

Since web and application servers will run on the same machine, we use a Unix socket to communicates with the web proxy server via the *WSGI* protocol instead of a network port. This would need to be changed when the different server components operate on separate machines or in separate containers.

.. _application-server-requirements:

Requirements
^^^^^^^^^^^^

* `Python <https://www.python.org/>`_ (version 2.7): Ubuntu (up to version 14.04) and MacOSX come with Python included. However, installing a newer version (2.7.9 or higher) and running the server in a virtual environment is recommended. On MacOSX make sure you use the version installed via `Homebrew`!
* `Pip <https://pip.pypa.io/en/stable/>`_: The Python package manager is typically already installed with the Python distributions, but we need to update it to make sure we use the most recent version.

    On Ubuntu:

    .. code-block:: none

        sudo apt-get update
        sudo apt-get -y install python-pip python-setuptools python-dev build-essential
        sudo apt-get -y install libreadline-gplv2-dev libncursesw5-dev libssl-dev libsqlite3-dev tk-dev libgdbm-dev libc6-dev libbz2-dev

        wget https://www.python.org/ftp/python/2.7.13/Python-2.7.13.tgz
        tar -xvf Python-2.7.13.tgz
        cd Python-2.7.13
        ./configure
        make
        sudo make install  # sudo make altinstall

        sudo pip install --upgrade pip
        sudo pip install --upgrade setuptools

    On MacOSX::

        brew update
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

    sudo pip install virtualenvwrapper

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

and configure *uWSGI* in ``~/.tmaps/uwsgi.ini``:

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
    lazy-apps = true

Ensure that the server runs in `gevent <http://www.gevent.org/>`_ mode and adapt configurations according to available computational resources.

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


.. note:: This approach assumes that defined your environement in ``~/.bash_profile``.


.. _application:

Application
-----------

The actual `TissueMAPS` Python web application (available via the ``tmserver`` package) is implemented in the `Flask <http://flask.pocoo.org/>`_ micro-framework.

.. _application-requirements:

Requirements
^^^^^^^^^^^^

* `PostgreSQL <http://postgresxl.org/>`_ (version 9.6 or higher) with `Citus <https://www.citusdata.com/>` (version 6.0 or higher) and `Postgis <http://postgis.net/>` (version 2.2 or higher) extensions:

    On Ubuntu:

    .. code-block:: none

        curl https://install.citusdata.com/community/deb.sh | sudo bash
        sudo apt-get -y install postgresql-9.6-citus

        sudo apt-get -y install postgresql-9.6-postgis-2.2 postgresql-9.6-postgis-scripts postgresql-contrib-9.6 postgresql-server-dev-all postgresql-client

        echo 'export "PATH=$PATH:/usr/lib/postgresql/9.6/bin"' >> ~/.bash_profile
        source ~/.bash_profile


    On MacOSX:

    .. code-block:: none

        brew install citus

        # Postgis extension
        brew install pex
        brew install gettext && brew link -f gettext
        pex init
        pex -g /usr/local/opt/postgresql install postgis

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

* `R <https://www.r-project.org/>`_ (version 3.3.2 or higher): optional - only required for support of R Jterator modules

    On Ubuntu (examplified here for 14.04 "Trusty"):

    .. code-block:: none

        sudo sh -c 'echo "deb http://cran.rstudio.com/bin/linux/ubuntu trusty/" >> /etc/apt/sources.list'
        gpg --keyserver keyserver.ubuntu.com --recv-key E084DAB9
        gpg -a --export E084DAB9 | sudo apt-key add -
        sudo apt-get update
        sudo apt-get -y install r-base r-base-dev

    On MacOSX::

        brew tap homebrew/science
        brew install Caskroom/cask/xquartz
        brew install r

* other:

    On Ubuntu::

        sudo apt-get -y install libxml2-dev libxslt1-dev zlib1g-dev libssl-dev libffi-dev libgeos-dev

.. _application-installation:

Installation
^^^^^^^^^^^^

Install the *tmserver* application via `pip`::

    % pip install tmserver
    mkdir tmserver
    cd tmserver
    git clone https://github.com/TissueMAPS/TmServer.git .
    
    %install Cython: 
    pip install Cython

    and then run the script:

    https://github.com/TissueMAPS/TissueMAPS#installation-of-tissuemaps-python-packages-during-pre-release-phase

.. _application-configuration:

Configuration
^^^^^^^^^^^^^

.. _application-configuration-postgresql:

PostgreSQL
++++++++++

Define the data location (here demonstrated for `PostgreSQL` version 9.6):

    On Ubuntu (as ``postgres`` user):

        .. code-block:: none

            To create postgres user:
            
            sudo -u postgres psql postgres
            \password postgres
            \q
            
            To access the postgres user:
            
            sudo su - postgres

            export DATA_DIRECTORY=/var/lib/postgresql/9.6
            export LOG_DIRECTORY=/var/log/postgresql

    On MacOsX (as current user):

        .. code-block:: none

            export DATA_DIRECTORY=/usr/local/var/lib/postgresql/9.6
            export LOG_DIRECTORY=/usr/local/var/log/postgresql


Initialize a ``citus`` `database cluster <https://www.postgresql.org/docs/current/static/creating-cluster.html>`_ and start the servers for *master* and *workers*:

    .. code-block:: none

        mkdir -p $LOG_DIRECTORY

        mkdir -p $DATA_DIRECTORY/master
        initdb -D $DATA_DIRECTORY/master

        mkdir -p $DATA_DIRECTORY/worker
        initdb -D $DATA_DIRECTORY/worker


Activate the ``citus`` extension:

    .. code-block:: none

        echo "shared_preload_libraries = 'citus'" >> $DATA_DIRECTORY/master/postgresql.conf
        echo "shared_preload_libraries = 'citus'" >> $DATA_DIRECTORY/worker/postgresql.conf


Start the database cluster and create the default database:

    .. code-block:: none

        pg_ctl -D $DATA_DIRECTORY/master -o "-p 5432" -l $LOG_DIRECTORY/postgresql-9.6-master.log start
        pg_ctl -D $DATA_DIRECTORY/master -o "-p 9700" -l $LOG_DIRECTORY/postgresql-9.6-worker.log start

        # On Ubuntu the "postgres" database typically already exists
        createdb -p 5432 $(whoami)
        createdb -p 9700 $(whoami)


Create ``tissuemaps`` user with login permissions on the master and set a password when prompted:

    .. code-block:: none

        createuser -p 5432 -l -P tissuemaps
        createuser -p 9700 -l -P tissuemaps


Then create the ``tissuemaps`` database that's owned by the ``tissuemaps`` user:

    .. code-block:: none

        createdb -p 5432 -o tissuemaps tissuemaps
        createdb -p 9700 -o tissuemaps tissuemaps


Add ``citus``, ``postgis`` and ``hstore`` extensions:

    .. code-block:: none

        psql -p 5432 tissuemaps -c "CREATE EXTENSION citus;"
        psql -p 9700 tissuemaps -c "CREATE EXTENSION citus;"

        psql -p 5432 tissuemaps -c "CREATE EXTENSION postgis;"
        psql -p 9700 tissuemaps -c "CREATE EXTENSION postgis;"

        psql -p 5432 tissuemaps -c "CREATE EXTENSION hstore;"
        psql -p 9700 tissuemaps -c "CREATE EXTENSION hstore;"

Connect to the *master* database and add *worker* node:

    .. code-block:: none

        psql -p 5432 tissuemaps -c "SELECT * from master_add_node('localhost', 9700);"

        psql -p 5432 tissuemaps -c "select * from master_get_active_worker_nodes();"


Now, the distributed database is ready to use and you can connect to the ``tissuemaps`` database running on the *master* node (``localhost`` on port ``5432``) as ``tissuemaps`` user:

    .. code-block:: none

        psql -p 5432 tissuemaps tissuemaps


.. tip:: It is convenient to use a `pgpass file <https://www.postgresql.org/docs/current/static/libpq-pgpass.html>`_ to be able to connect to the database without having to type the password every time:

    .. code-block:: none

        echo 'localhost:5432:tissuemaps:tissuemaps:XXX' > ~/.pgpass
        chmod 0600 ~/.pgpass


.. tip:: You may also want to add an alias to ``~/.bash_profile`` to simplify connecting to the database via the ``psql`` console:

    .. code-block:: bash

        echo 'alias db="psql -h localhost -p 5432 tissuemaps tissuemaps"' >> ~/.bash_profile
        . ~/.bash_profile

Restarting database servers:

    On Ubuntu (via ``service``):

    .. code-block:: none

        # Starts database clusters automatically upon startup
        sudo update-rc.d postgresql enable

        # Restart database clusters
        sudo service postgresql restart

    On MacOSX (via shell script):

    .. code-block:: bash

        #!/bin/bash

        DATA_DIRECTORY=/usr/local/var/lib/postgresql/9.6
        LOG_DIRECTORY=/usr/local/var/log/postgresql

        MASTER_PORT=5432
        WORKER_PORT=9700

        echo "=>restart master database server on port $MASTER_PORT"
        pg_ctl restart -D $DATA_DIRECTORY/master -o "-p $MASTER_PORT" -l $LOG_DIRECTORY/postgresql-9.6-master.log

        echo "=>restart worker database server on port $WORKER1_PORT"
        pg_ctl restart -D $DATA_DIRECTORY/worker -o "-p $WORKER1_PORT" -l $LOG_DIRECTORY/postgresql-9.6-worker.log


When using a mounted filesystem for data storage, you can create a symlink to ``data_dirctory`` or use an alternative directory. Make sure, however, to set the correct permissions for the parent directory of the desired data directory. For more information please refer to the PostgreSQL online documentation on `file locations <https://www.postgresql.org/docs/current/static/runtime-config-file-locations.html>`_ and `creation of a new database cluster <https://www.postgresql.org/docs/9.6/static/app-initdb.html>`_.



.. _application-configuration-tissuemaps:

TissueMAPS
++++++++++

Create a `TissueMAPS` configuration file ``~/.tmaps/tissuemaps.cfg`` and set the ``db_password`` parameter (replace ``XXX`` with the actual password you defined above):

.. code-block:: ini

    [DEFAULT]
    db_user = tissuemaps
    db_port = 5432
    db_password = XXX

    [tmlib]
    storage_home = /storage/experiments


Additional parameters may need to be set. Please refer to :class:`LibraryConfig <tmlib.config.LibraryConfig>` and :class:`ServerConfig <tmserver.config.ServerConfig>`.
The default configuration assumes, for example, sets :attr:`storage_home <tmlib.config.LibraryConfig.storage_home>` to ``/data/experiments`` (because that's were an additional volume would be mounted upon automated deployment). You may either configure an alternative directory or create the default directory (exemplified here for ``ubuntu`` user)::

     sudo mkdir -p /storage/experiments
     sudo chown -R $(whoami) /storage/experiments

Finally, populate the ``tissuemaps`` database with the tables defined in the :doc:`tmlib.models` package::

    tm_create_tables

and create a *TissueMAPS* user account for yourself::

    tm_add user --name XXX --password XXX --email XXX

.. note:: Depending on where the ``tmlibrary`` package got installed, you may need to add the location of the executables to the ``PATH``: e.g. ``export PATH=$PATH:~/.local/bin``.


.. _application-configuration-gc3pie:

GC3Pie
++++++

Under the hood, `TissueMAPS` uses `GC3Pie <http://gc3pie.readthedocs.io/en/latest/programmers/index.html>`_ for computational job management. The program provides a high-level API around different cluster backends, but can also submit jobs to localhost.

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

    tm_server -vv

The client installation also provides a `development web server <https://www.npmjs.com/package/gulp-webserver>`_ to dynamically build client code with live reload functionality::

    cd ~/tmui/src
    gulp

This will automatically start the application server on port 5002 and the web server on port 8002. To access the website, point your browser to ``http://localhost:8002/``.

Both dev servers provide live reload functionality. They will auto-watch files and rebuild code upon changes, which is useful for local development and testing.
