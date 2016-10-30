# TmLibrary - TissueMAPS library for distibuted image processing routines.
# Copyright (C) 2016  Markus D. Herrmann, University of Zurich and Robin Hafen
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
Small utility script to create the database schema defined by the models
contained in this package.
Before runnign this tool make sure that the database and database user exist
and that the tables are not present alraedy.
The postgres utilities 'createdb' and 'dropdb' could prove useful to
create/recreate the database as necessary.

"""

if __name__ == "__main__":
    import sqlalchemy
    import argparse
    from tmlib.models.base import Model

    parser = argparse.ArgumentParser(
        description='Schema creation utility for models used in TissueMAPS.')

    parser.add_argument(
        '--create', action='store_true', default=False,
        help='If the schema should be created')
    parser.add_argument(
        '--dbname', help='The database name', default='tissuemaps')
    parser.add_argument(
        '--dbuser', help='The database user')
    parser.add_argument(
        '--dbpass', help='The database user\'s password')
    parser.add_argument(
        '--dbport', help='The database port', type=int, default=5432)
    parser.add_argument(
        '--dbhost', help='The database host', default='localhost')

    args = parser.parse_args()

    db_uri = 'postgresql://{user}:{passw}@{host}:{port}/{dbname}'.format(
        user=args.dbuser,
        passw=args.dbpass,
        port=args.dbport,
        dbname=args.dbname)

    if args.create:
        print 'Creating schema'
        engine = sqlalchemy.create_engine(db_uri)
        Model.metadata.create_all(engine)
