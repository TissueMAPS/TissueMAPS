tissueMAPS server
=================

Initial setup (OSX)
-------------

Install `tmlib` and server-specific packages:

    $ cd TissueMAPS/server
    $ workon tmaps  # created when TmLibrary was installed
    $ pip install -r tmaps/requirements/requirements.txt


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

### Config file creation

You now have to create a new config file where all the settings for the
TissueMAPS server are stored. There are template files that can be copied and
adjusted.

    $ cp config/dev.py.template config/dev.py
    
Fill in the content of this template as needed. Then, set the environment
variable `TMAPS_SETTINGS` to point to this config file.

    $ export TMAPS_SETTINGS=config/dev.py

You can have multiple configs and switch between them by resetting this
environment variable.

### Initial database creation

Create a new database called 'tissuemaps' using pgadmin3 or the createdb cli tool.

Make sure that the database access information is set in the config file accordingly (variable `SQLALCHEMY_DATABASE_URI`).

If you installed postgres via postgres.app there is already a databaser superuser with the same username/pw combination as your system's user.
If you installed postgres via brew, you need to create the user account specified in your `config/dev.py` file:

    $ createuser -P -s -e your_name

Finally, initialize all tables with:

    $ python manage.py db createtables

There is also a small shortcut script to recreate the db after you change the schema:

    $ sh scripts/recreate_db.sh

Note that you need to close any existing connection (e.g. with pgAdmin) if you want to drop tables!


Database migrations # TODO
-------------------

Create a new migration:

    $ python manage.py migrate init
