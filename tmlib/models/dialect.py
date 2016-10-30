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
from sqlalchemy import func, text, cast
from sqlalchemy.ext.compiler import compiles
from sqlalchemy_utils.expressions import array_agg
from sqlalchemy.schema import DropTable, CreateTable
from sqlalchemy.schema import UniqueConstraint, PrimaryKeyConstraint
from sqlalchemy.dialects.postgresql.psycopg2 import PGDialect_psycopg2


class PGXLDialect_psycopg2(PGDialect_psycopg2):

    '''SQLAlchemy dialect for `PostgresXL <http://www.postgres-xl.org/>`_
    database cluster.
    '''
    name = 'postgresxl'


@compiles(CreateTable, 'postgresxl')
def _compile_create_table(element, compiler, **kwargs):
    table = element.element
    logger.info('create table "%s"', table.name)
    distribute_by_hash = 'distribute_by_hash' in table.info
    if distribute_by_hash:
        distribution_column = table.info['distribute_by_hash']
        # The distributed column must be part of the UNIQUE and
        # PRIMARY KEY constraints
        # TODO: consider hacking "visit_primary_key_constraint" and
        # "visit_unique_constraint" instead
        for c in table.constraints:
            if (isinstance(c, PrimaryKeyConstraint) or
                    isinstance(c, UniqueConstraint)):
                if distribution_column not in c.columns:
                    c.columns.add(table.columns[distribution_column])
        # The distributed column must be part of any INDEX
        for i in table.indexes:
            if distribution_column not in i.columns:
                i.columns.add(table.columns[distribution_column])
    sql = compiler.visit_create_table(element)
    if distribute_by_hash:
        logger.info(
            'distribute table "%s" by hash "%s"', table.name,
            distribution_column
        )
        sql += ' DISTRIBUTE BY HASH(' + distribution_column + ')'
    else:
        logger.info(
            'distribute table "%s" by replication', table.name
        )
        sql += ' DISTRIBUTE BY REPLICATION'
    return sql


@compiles(DropTable, 'postgresxl')
def _compile_drop_table(element, compiler, **kwargs):
    table = element.element
    logger.debug('drop table "%s" with cascade', table.name)
    return compiler.visit_drop_table(element) + ' CASCADE'


@compiles(array_agg, 'postgresxl')
def compile_array_agg(element, compiler, **kw):
    compiled = "%s(%s)" % (element.name, compiler.process(element.clauses))
    if element.default is None:
        return compiled
    return str(func.coalesce(
        text(compiled),
        cast(postgresql.array(element.default), element.type)
    ).compile(compiler))
