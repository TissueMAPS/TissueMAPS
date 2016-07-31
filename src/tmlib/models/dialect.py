from sqlalchemy.dialects.postgresql.psycopg2 import PGDialect_psycopg2

class PGXLDialect_psycopg2(PGDialect_psycopg2):

    '''SQLAlchemy dialect for `PostgresXL <http://www.postgres-xl.org/>`_
    database cluster.
    '''
    name = 'postgresxl'
