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
# from sqlalchemy.dialects.postgresql.psycopg2 import PGDialect_psycopg2

from tmlib.errors import DataModelError
from tmlib import cfg


logger = logging.getLogger(__name__)


def _update_table_constraints(table, distribution_column):
    # Distribution column must be part of UNIQUE and PRIMARY KEY constraints.
    for c in table.constraints:
        if (isinstance(c, PrimaryKeyConstraint) or
                isinstance(c, UniqueConstraint)):
            if distribution_column not in c.columns:
                c.columns.add(table.columns[distribution_column])
    return table


@compiles(CreateTable, 'postgresql')
def _compile_create_table(element, compiler, **kwargs):
    table = element.element
    logger.debug('create table "%s"', table.name)
    distribute_by_hash = 'distribute_by_hash' in table.info
    distribute_by_replication = 'distribute_by_replication' in table.info
    if distribute_by_hash or distribute_by_replication:
        if distribute_by_hash:
            distribution_column = table.info['distribute_by_hash']
            table = _update_table_constraints(table, distribution_column)
            logger.debug(
                'distribute table "%s" by hash "%s"', table.name,
                distribution_column
            )
            # No replication of tables.
            sql = 'SET citus.shard_replication_factor = 1;\n'
            sql += 'SET citus.shard_count = {n};\n'.format(n=30*cfg.db_nodes)
            sql += compiler.visit_create_table(element)
            # More aggressive autovacuum for large tables?
            if table.info['colocated_table']:
                distributed_sql = "'{s}.{t}','{c}',colocate_with=>'{s}.{t2}'".format(
                    s=table.schema, t=table.name, c=distribution_column,
                    t2=table.info['colocated_table']
                )
            else:
                distributed_sql = "'{s}.{t}', '{c}'".format(
                    s=table.schema, t=table.name, c=distribution_column
                )
            sql += ';\nSELECT create_distributed_table(%s);' % (distributed_sql)

        elif distribute_by_replication:
            # The first column will be used as partition column and must be
            # included in UNIQUE and PRIMARY KEY constraints.
            # NOTE: This assumes that "id" column is the first column. This is
            # ensured by the IdMixIn on MainModel and ExperimentModel base
            # classes, but may get screwed up by additional mixins.
            if not element.columns[0].element.primary_key:
                raise DataModelError(
                    'First column of table "%s" must be the PRIMARY KEY '
                    'to be able to distribute the table by replication.' %
                    table.name
                )
            table = _update_table_constraints(table, 'id')
            logger.debug('distribute table "%s" by replication', table.name)
            sql = 'SET citus.shard_replication_factor = %s;\n' % cfg.db_nodes
            sql += compiler.visit_create_table(element)
            sql += ';\nSELECT create_reference_table(\'%s.%s\');' % (
                table.schema, table.name
            )
        else:
            sql = compiler.visit_create_table(element)
    else:
        sql = compiler.visit_create_table(element)
    # NOTE: Tables don't have to be distributed.
    # If they don't get distributed, they live happily as normal
    # PostgreSQL tables on the master node.
    return sql


@compiles(DropTable, 'postgresql')
def _compile_drop_table(element, compiler, **kwargs):
    table = element.element
    logger.debug('drop table "%s" with cascade', table.name)
    return compiler.visit_drop_table(element) + ' CASCADE'


@compiles(array_agg, 'postgresql')
def _compile_array_agg(element, compiler, **kw):
    compiled = "%s(%s)" % (element.name, compiler.process(element.clauses))
    if element.default is None:
        return compiled
    return str(func.coalesce(
        text(compiled),
        cast(postgresql.array(element.default), element.type)
    ).compile(compiler))


def compile_distributed_query(sql):
    '''Compiles a *SQL* query for modification of a hash distributed Citus table.

    Parameters
    ----------
    sql: str
        query

    Returns
    -------
    str
        compiled query
    '''
    # This is required for modification of distributed tables
    # TODO: compile UPDATE and DELETE queries in dialect
    return '''
        SELECT master_modify_multiple_shards($$
            {query}
        $$)
    '''.format(query=sql)
