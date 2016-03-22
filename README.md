tissueMAPS server
=================

Initial setup (OSX)
-------------

Install all flask packages:

    $ cd TissueMAPS/server
    $ mkvirtualenv tmaps
    $ pip install -r tmaps/requirements/requirements.txt

### Postgres

Install the postgres database server.


#### Via postgres.app (easiest)

    Install postgres.app from [](http://postgresapp.com/).
    
You also need to do the following:

    sudo ln -s /Applications/Postgres.app/Contents/Versions/9.4/lib/libpq.5.dylib /usr/lib

Add the command line tools to the PATH:

    echo 'export PATH=$PATH:/Applications/Postgres.app/Contents/Versions/9.4/bin' >> ~/.bash_profile

For a management GUI install pgAdmin from [](http://www.postgresql.org/ftp/pgadmin3/release/v1.20.0/osx/).

Add a new connection with "File > Add Server" and insert `localhost` as the host and your system user name and passwort for the db user.

#### Via brew

    $ brew install postgres

Install a manager package to start/stop postgres ([link](https://robots.thoughtbot.com/starting-and-stopping-background-services-with-homebrew)):

    $ brew tap gapple/services

Start postgres:

    $ brew services start postgres

This starts postgres with the default config file at `/usr/local/var/postgres/postgresql.conf` on port 5432.

### Initial database creation

Now, create a new database called 'tissuemaps' using pgadmin3 or the createdb cli tool.

    $ createdb tissuemaps

Make sure that the database access information is set in `tmaps/config/dev.py` accordingly.
Depending on your setup, this could look something like this:

    POSTGRES_DB_USER = 'your name'
    POSTGRES_DB_PASSWORD = 'your pw'
    POSTGRES_DB_NAME = 'tissuemaps'
    POSTGRES_DB_HOST = 'localhost'
    POSTGRES_DB_PORT = 5432
    DEBUG = True

If you installed postgres via postgres.app there is already a databaser superuser with the same username/pw combination as your system's user.
If you installed postgres via brew, you need to create the user account specified in your `config/dev.py` file:

    $ createuser -P -s -e your_name

Finally, initialize all tables with:

    $ python manage.py create_tables

Add some dummy data (like a user with name 'testuser'):

    $ python manage.py populate_db

There is also a small shortcut script to recreate the drop and repopulate the db after you change the schema:

    $ sh scripts/recreate_db.sh

Note that you need to close any existing connection (e.g. with pgAdmin) if you want to drop tables!


Database migrations # TODO
-------------------

Create a new migration:

    $ python manage.py migrate init


Required structure of experimental data
---------------------------------------

Folder structure:

    {experiment_name}/
        data.h5
        id_tables/
            ROW00001_COL000001.npy
            ...
        id_pyramids/ (currently 'layermod_src/')
        layers/

For structure of `data.h5` see [datafusion]().
