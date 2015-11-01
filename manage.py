#!/usr/bin/env python
# encoding: utf-8

from flask.ext.script import Manager
from flask.ext.migrate import Migrate, MigrateCommand

from tmaps.appfactory import create_app
from tmaps.extensions.database import db

# Execute all model definitions
from tmaps.models import *

app = create_app()

migrate = Migrate(app, db)
manager = Manager(app)

# Add a new command to expose options provided by Alembic
manager.add_command('migrate', MigrateCommand)


@manager.command
def repl():
    import sys
    from werkzeug import script
    def make_shell():
        from tmaps.appfactory import create_app
        app = create_app()
        ctx = app.test_request_context()
        ctx.push()
        from tmaps import models
        from tmaps.extensions.database import db
        return dict(app=app, ctx=ctx, models=models, db=db)
    script.make_shell(make_shell, use_ipython=True)()


@manager.command
def create_tables():
    """A command to initialize the tables in the database specified by the
    config key 'SQLALCHEMY_DATABASE_URI'.

    Usage:

        $ python manage.py create_db

    """
    db.create_all()


@manager.command
def populate_db():
    """Insert some default values into the database. Run this command
    after `create_tables`."""

    with app.app_context():
        # Add admin user
        u1 = User(name='testuser',
                 email='testuser@something.com',
                 location='/Users/robin/Dev/TissueMAPS/expdata',
                 password='123')
        u2 = User(name='testuser2',
                  email='testuser2@something.com',
                 location='/Users/robin/Dev/TissueMAPS/expdata/somethingelse',
                  password='123')
        db.session.add(u1)
        db.session.add(u2)
        db.session.commit()

        a = AppState(name='Nice findings',
                     blueprint='{"bla": 123}',
                     owner_id=u1.id,
                     description='Look at this, how nice!')
        a2 = AppState(name='Some other findings by testuser2',
                      blueprint='{"bla": 123}',
                      owner_id=u2.id,
                      description='blablabla very nice')
        db.session.add(a)
        db.session.add(a2)
        db.session.commit()

        state = AppStateShare(recipient_user_id=u1.id,
                              donor_user_id=u2.id,
                              appstate_id = a2.id)

        db.session.add(state)
        db.session.commit()


        e1 = Experiment(name='150316-30min-PBS',
                        description='Very nice exp',
                        owner=u1,
                        location='/Users/robin/Dev/TissueMAPS/expdata/150316-30min-PBS')
        db.session.add(e1)
        db.session.commit()

if __name__ == '__main__':
    manager.run()
