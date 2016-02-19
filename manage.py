#!/usr/bin/env python
# encoding: utf-8
import yaml
from subprocess import call

import flask
from flask.ext.script import Manager
from flask.ext.migrate import Migrate, MigrateCommand

from tmaps.appfactory import create_app
from tmaps.extensions.database import db

# Execute all model definitions
from tmaps.models import *


cfg = flask.Config(p.realpath(p.dirname(__file__)))
cfg.from_envvar('TMAPS_SETTINGS')

manager = Manager(lambda: create_app(cfg))  # main manager

# Create sub manager for database commands
db_manager = Manager(lambda: create_app(cfg))

migrate = Migrate(lambda: create_app(cfg), db)
# Add a new command to expose options provided by Alembic
db_manager.add_command('migrate', MigrateCommand)


@manager.command
def repl():
    """Start a REPL that can be used to interact with the models
    of the application."""
    app = create_app(cfg)
    from werkzeug import script
    def make_shell():
        ctx = app.test_request_context()
        ctx.push()
        from tmaps import models
        return dict(app=app, ctx=ctx, models=models, db=db)
    script.make_shell(make_shell, use_ipython=True)()


@db_manager.command
def create_tables():
    """A command to initialize the tables in the database specified by the
    config key 'SQLALCHEMY_DATABASE_URI'.

    Usage:

        $ python manage.py create_db

    """
    db.create_all()


@db_manager.command
def insert_data(yaml_file):
    """Insert some records values into the database.

    This command has to be run after after `create_tables`.

    Arguments
    ---------
    yaml_file : str
        The path to a yaml file with the following structure:

        records:
            - ClassName:
                arg1: value1
                arg2: value2
                ...
            ...

    """
    app = create_app(cfg)

    if yaml_file is None or yaml_file == '':
        print 'No yaml_file supplied, will not insert any data. '
        return

    with open(yaml_file, 'r') as f:
        sample_data = yaml.load(f)

        with app.app_context():
            for rec in sample_data['records']:
                class_name = rec['class']
                constr_args = rec['args']
                model_constr = globals()[class_name]

                for k, v in constr_args.items():
                    if type(v) is dict:
                        obj_class = v['class']
                        obj_model = globals()[obj_class]
                        lookup_properties = v['lookup_props']
                        arg_obj = db.session.query(obj_model).filter_by(**lookup_properties).first()
                        constr_args[k] = arg_obj

                obj = model_constr(**constr_args)

                print 'Inserting new object of class "%s" with properties:' % class_name
                for k, v in constr_args.items():
                    print '\t%s: %s' % (k , str(v))
                print

                db.session.add(obj)
                db.session.commit()


# Add submanager to manage database commands under the prefix db
manager.add_command('db', db_manager)


if __name__ == '__main__':
    manager.run()
