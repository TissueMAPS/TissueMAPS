TissueMAPS server
=================

REST API design
---------------

**DEPRECATED**: Update this section for the changed API design that is again based on
the structure `/api/experiments/XXXX/channel-layers/YYYY`.

The TissueMAPS server provides a REST API that is used by the TissueMAPS
client. The structure of the API is as follows and should be kept when
adding any functionality. As an example, consider the `Experiment` resource:

- `GET /api/experiments` will get all experiments for the current user. The
  response payload will have a `data` attribute with a list of serialized experiments.
- `GET /api/experiments/0` will get the experiment with id 0. The response
  payload will have a `data` attribute consisting of a single experiment (no
  list!).
- `GET /api/experiments?id=0` is the same as the query above but will return a
  list. Properties (here *id*) can be comma-separated lists.
- `POST /api/experiments` will create a new experiment for the current user.
  Required data is provided using the request payload. The response will
  contain a data attribute with the serialized experiment (with a newly created
  id).
- `PUT /api/experiments/0/some-action` will call a specific action for the
  experiment with id 0.

Note that there is no nesting of resources, e.g. the route
`/api/experiments/0/plates` does not exist.
Instead this query would look like this: `GET /api/plates?experiment_id=0`.
Also, if a plate for experiment 0 should be created the query should look like
this: `POST /api/plates { "experiment_id": 0, ... }.


Setup (development) for OSX
---------------------------

### Install requirements

Create a virtual environment like so:

    $ cd TissueMAPS/server
    $ mkvirtualenv tmaps  # or any other name

Install all python requirements into the virtual environment:

    $ pip install -r requirements/requirements.txt

In addition you need to install the TissueMAPS library manually. Please
consult [https://github.com/TissueMAPS/TmLibrary](https://github.com/TissueMAPS/TmLibrary) to get instructions on how to do this.


### Install the database server

#### Via postgres.app (easiest)

    Install postgres.app from [](http://postgresapp.com/).
    
You also need to do the following:

    sudo ln -s /Applications/Postgres.app/Contents/Versions/9.5/lib/libpq.5.dylib /usr/lib

Add the command line tools to the PATH:

    echo 'export PATH=$PATH:/Applications/Postgres.app/Contents/Versions/9.5/bin' >> ~/.bash_profile

For a GUI-based management tool install [pgAdmin](http://www.postgresql.org/ftp/pgadmin3/release/v1.20.0/osx/) or [postico](https://eggerapps.at/postico/).

#### Via brew

    $ brew install postgres

Install a manager package to start/stop postgres ([link](https://robots.thoughtbot.com/starting-and-stopping-background-services-with-homebrew)):

    $ brew tap gapple/services

Start postgres:

    $ brew services start postgres

This starts postgres with the default config file at `/usr/local/var/postgres/postgresql.conf` on port 5432.

### Create the config file

You now have to create a new config file where all the settings for the
TissueMAPS server are stored. 
This file is located under `tmaps/dev.py.template`.
Copy this file and edit it according to your setup.

    $ cp config/dev.py.template config/dev.py
    
Fill in the content of this file as needed. Then, set the environment
variable `TMAPS_SETTINGS` to point to this config file.

    $ export TMAPS_SETTINGS=devconfig.py

You can have multiple configs (for example with different database
configurations) and switch between them easily by resetting this
environment variable.

### Database creation

Create a new database called 'tissuemaps' using pgadmin3 or the `createdb` CLI tool.

Make sure that the database access information is set in the config file accordingly (variable `SQLALCHEMY_DATABASE_URI`).

If you installed postgres via postgres.app there is already a databaser superuser with the same username/pw combination as your system's user.
If you installed postgres via brew, you need to create the user account specified in your `config/dev.py` file:

    $ createuser -P -s -e your_name

Install the postgis extension:

    $ echo 'CREATE EXTENSION postgis;' | psql -d tissuemaps

Finally, let sqlalchemy create all tables with:

    $ python manage.py db createtables


There is also a small shortcut script to recreate the db after you change the schema:

    $ sh scripts/recreate_db.sh

Note that you need to close any existing connection (e.g. with pgAdmin) if you want to drop tables!

Running tests
-------------

To run the tests you need to create a separate configuration file that
specifies `TESTING = True` and that points to a **DIFFERENT** database whose content can safely be modified by the testing code.

The environment variable `TMAPS_SETTINGS_TEST` should be used to publish the configuration file's location:

    $ export TMAPS_SETTINGS_TEST=/path/to/tmaps_settings_test.py

From within the server subdirectory execute:

    $ py.test [-s]

Use the `-s` flag to see any output.

Setup (production) for Ubuntu (deprecated)
------------------------------------------

Execute the following commands on your machine running Ubuntu 14.04:

    $ sudo apt-get update
    $ sudo apt-get install git  # version 1.9.1
    $ sudo apt-get install build-essential
    $ git clone --recursive https://github.com/TissueMAPS/TissueMAPS

    $ cd TissueMAPS/client
    $ sudo apt-get install nodejs  # version v0.10.25
    $ sudo apt-get install npm  # version 1.3.10

Gulp tries to call the binary `node` but ubuntu installs it as `nodejs`, so we
create a link:
    $ sudo ln -s /usr/bin/nodejs /usr/bin/node
    $ npm install  # from within client dir: get tools needed to build client

Now you can execute the next command and just supply the credentials
manually.

    $ node_modules/bower/bin/bower install  # fetch libs

Build client code:

    $ node_modules/gulp/bin/gulp.js build

The resulting directory `build` contains all the client side code of
TissueMAPS. We move it into a new directory where it will eventually be served
by nginx:

    $ cd ~/TissueMAPS
    $ mkdir server/static
    $ cp -r client/_dist server/static/tmaps

Installing the other deps: nginx and redis (from source):

    $ sudo apt-get install nginx redis

    $ cd ~
    $ wget http://download.redis.io/redis-stable.tar.gz
    $ tar xvzf redis-stable.tar.gz
    $ cd redis-stable
    $ make
    $ sudo make install

Before starting the final server, you need to remember to actually start redis:

    $ redis-server

Now to uwsgi:

    $ sudo pip install uwsgi

If on ubuntu 14.04 postgres 9.4 isn't in the repository (14.10 should be fine), but TissueMAPS depends
on it. In this case we need to add it:

    $ sudo vim /etc/apt/sources.list.d/pgdg.list

Add the line:

    deb http://apt.postgresql.org/pub/repos/apt/ trusty-pgdg main

Then:

    $ wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | \
      sudo apt-key add -
    $ sudo apt-get update
    $ apt-get install postgresql-9.5

For more details, see: [](http://www.postgresql.org/download/linux/ubuntu/).

**NOTE**: The PostGIS extension for postgresql has to be installed as well.

    $ cd ~

Installing the requirements via the requirements.txt file doesn't work on
ubuntu since some have to be installed via apt.

    ($ sudo pip install TissueMAPS/server/requirements/requirements.txt)

So doing it manually:

    $ sudo apt-get install python-numpy python-scipy python-matplotlib ipython ipython-notebook python-pandas python-sympy python-nose
    $ sudo easy_install -U setuptools
    $ sudo pip install flask_sqlalchemy hashids passlib gc3pie flask_jwt flask_redis sklearn flask_script flask_migrate

psycopg2 won't install via pip on Ubuntu since it needs the dev package of
postgres:

    $ sudo apt-get install postgresql-server-dev-9.5
    $ sudo apt-get install python-psycopg2

    $ Somehow install tmlib

    $ cp tmaps/config/tmaps_settings.py.template tmaps_settings_PRODUCTION.py


Create the user tissuemaps and a db with the same name which is also owned by
the tissuemaps user (-d: user can create dbs, -P: prompt for password):

    $ sudo -u postgres createuser tissuemaps -dP
    $ sudo -u postgres createdb -O tissuemaps tissuemaps


Enter the db info in the server config:

    $ vi tmaps_settings_PRODUCTION.py

    $ export TMAPS_SETTINGS=~/TissueMAPS/server/tmaps_settings_PRODUCTION.py

Create the DB schema and insert test data:

    $ python manage.py create_tables  # create tables in empty db
    $ python manage.py populate_db  # insert dev data (testuser)


gc3libs has a bug when it is used with postgres-based sessions. For now:

    $ vi /usr/local/lib/python2.7/dist-packages/gc3libs/persistence/sql.py

Search for BLOB in the constructor and rename to LargeBinary.

Create initial gc3pie config:

    $ gservers

Try if this works by running the dev server:

    $ python wsgi.py

Then, configuring uwsgi:
(The following is taken from [this link](https://www.digitalocean.com/community/tutorials/how-to-serve-flask-applications-with-uwsgi-and-nginx-on-ubuntu-14-04))

    $ vi uwsgi.ini

Add the contents:

    [uwsgi]
    module = wsgi:app

    master = true
    
    # Parallelization and concurrency
    processes = 5
    gevent = 100

    socket = nginx-comm.sock
    chmod-socket = 777 # CHANGE THIS TO 660 AND CHECK THAT NGINX HAS PERMISSION
    vacuum = true

    die-on-term = true
    
    # Overwrite default "www-data" group (important for SLURM job submission)
    gid = ubuntu
    
    # Capture environment for uWSGI ($env > ~/TissueMaps/server/environment.txt)
    for-readline = environment.txt
      env = %(_)
    endfor =


Now create an upstart scripts according to the link above.

    $ sudo vim /etc/init/tmaps-uwsgi.conf

Add the contents:

    description "uWSGI server instance configured to serve TissueMAPS"

    start on runlevel [2345]
    stop on runlevel [!2345]

    setuid parallels
    setgid www-data

    # If using a virtualenv:
    # env PATH=/home/parallels/TissueMAPS/server/venv
    chdir /home/parallels/TissueMAPS/server
    exec uwsgi --ini uwsgi.ini

Start the server:

    $ sudo start tmaps-uwsgi

Configuring nginx:

    $ sudo vim /etc/nginx/sites-available/tmaps

Add the contents:

    http {
        uwsgi_read_timeout 3600;
        client_max_body_size 1000M;
    }

    server {
        listen 80;
        server_name localhost;

        # pass all request to with /api prefix to uwsgi listening on
        # the unix socket nginx-comm.sock
        location /api/ {
            include uwsgi_params;
            uwsgi_pass unix:/usr/home/parallels/TissueMAPS/server/nginx-comm.sock;
        }

        # all non-API requests are file requests and should be served
        # from the built client dir.
        location / {
            root /usr/home/parallels/TissueMAPS/server/static/tmaps;
        }
    }

Enable the host by creating a link to `sites-enabled`:
    $ sudo ln -s /etc/nginx/sites-available/tmaps /etc/nginx/sites-enabled
    $ sudo rm /etc/nginx/sites-enabled/default  # Remove default nginx test page

Check syntax of the nginx file:

    $ sudo nginx -t

Restart nginx:

    $ sudo service nginx restart

Start uwsgi (directly, probably better to create a upstart script, see above):

    $ uwsgi --ini uwsgi.ini

Then access the server with a browser via port 80.


Database migrations # TODO
--------------------------

Create a new migration:

    $ python manage.py migrate init
