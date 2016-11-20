# TmLibrary - TissueMAPS library for distibuted image analysis routines.
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
import logging
from sqlalchemy import func, text, cast
from sqlalchemy.ext.compiler import compiles
from sqlalchemy_utils.expressions import array_agg
from sqlalchemy.schema import DropTable, CreateTable
from sqlalchemy.schema import UniqueConstraint, PrimaryKeyConstraint
from sqlalchemy.dialects.postgresql.psycopg2 import PGDialect_psycopg2

from tmlib.errors import DataModelError


logger = logging.getLogger(__name__)


def _update_table_constraints(table, distribution_column):
    # Distribution column must be part of UNIQUE and PRIMARY KEY constraints.
    for c in table.constraints:
        if (isinstance(c, PrimaryKeyConstraint) or
                isinstance(c, UniqueConstraint)):
            if distribution_column not in c.columns:
                c.columns.add(table.columns[distribution_column])
    # for i in table.indexes:
    #     if distribution_column not in i.columns:
    #         i.columns.add(table.columns[distribution_column])
    return table


class CitusDialect_psycopg2(PGDialect_psycopg2):

    '''*SQLAlchemy* dialect for
    `Citus <https://docs.citusdata.com/en/v6.0/index.html>`_ *PostgreSQL*
    extension.
    '''
    name = 'citus'


@compiles(CreateTable, 'citus')
def _compile_create_table(element, compiler, **kwargs):
    table = element.element
    logger.info('create table "%s"', table.name)
    distribute_by_hash = 'distribute_by_hash' in table.info
    distribute_by_replication = 'distribute_by_replication' in table.info
    if distribute_by_hash or distribute_by_replication:
        if table.foreign_keys:
            raise DataModelError(
                'Distributed table "%s" must not have FOREIGN KEY constraints.'
                % table.name
            )
        if distribute_by_hash:
            distribution_column = table.info['distribute_by_hash']
            table = _update_table_constraints(table, distribution_column)
            logger.info(
                'distribute table "%s" by hash "%s"', table.name,
                distribution_column
            )
            sql = compiler.visit_create_table(element)
            sql += ';SELECT create_distributed_table(\'%s\', \'%s\');' % (
                table.name, distribution_column
            )
        elif distribute_by_replication:
            # The first column will be used as partition column and must be
            # included in UNIQUE and PRIMARY KEY constraints.
            # NOTE: This assumes that "id" column is the first column. This is
            # ensured by the IdMixIn on MainModel and ExperimentModel base
            # classes, but may get screwed up by additional mixins.
            if not isinstance(element.columns[0].element, PrimaryKeyConstraint):
                raise DataModelError(
                    'First column of table "%s" must be the PRIMARY KEY '
                    'to be able to distribute the table by replication.' %
                    table.name
                )
            table = _update_table_constraints(table, 'id')
            logger.info('distribute table "%s" by replication', table.name)
            sql = compiler.visit_create_table(element)
            sql += ';SELECT create_reference_table(\'%s\');' % table.name
        else:
            sql = compiler.visit_create_table(element)
    else:
        sql = compiler.visit_create_table(element)
    # NOTE: In contrast to PostgresXL, tables don't have to be distributed.
    # If they don't get distributed, they live a happy live as normal
    # PostgreSQL tables on the master node.
    return sql



# class PGXLDialect_psycopg2(PGDialect_psycopg2):

#     '''SQLAlchemy dialect for `PostgresXL <http://www.postgres-xl.org/>`_
#     database cluster.
#     '''
#     name = 'postgresxl'


# @compiles(CreateTable, 'postgresxl')
# def _compile_create_table(element, compiler, **kwargs):
#     table = element.element
#     logger.info('create table "%s"', table.name)
#     distribute_by_hash = 'distribute_by_hash' in table.info
#     if distribute_by_hash:
#         distribution_column = table.info['distribute_by_hash']
#         table = _update_table_constraints(table, distribution_column)
#         logger.info(
#             'distribute table "%s" by hash "%s"', table.name,
#             distribution_column
#         )
#         sql = compiler.visit_create_table(element)
#         sql += ' DISTRIBUTE BY HASH(' + distribution_column + ')'
#     else:
#         # NOTE: In PostrgresXL every table needs to be distributed.
#         logger.info(
#             'distribute table "%s" by replication', table.name
#         )
#         sql = compiler.visit_create_table(element)
#         sql += ' DISTRIBUTE BY REPLICATION'
#     return sql


# @compiles(DropTable, 'postgresxl')
# def _compile_drop_table(element, compiler, **kwargs):
#     table = element.element
#     logger.debug('drop table "%s" with cascade', table.name)
#     return compiler.visit_drop_table(element) + ' CASCADE'


# @compiles(array_agg, 'postgresxl')
# def compile_array_agg(element, compiler, **kw):
#     compiled = "%s(%s)" % (element.name, compiler.process(element.clauses))
#     if element.default is None:
#         return compiled
#     return str(func.coalesce(
#         text(compiled),
#         cast(postgresql.array(element.default), element.type)
#     ).compile(compiler))

