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
from psycopg2 import sql
from sqlalchemy import func, text, cast
from sqlalchemy.ext.compiler import compiles
from sqlalchemy_utils.expressions import array_agg
from sqlalchemy.schema import DropTable, CreateTable
from sqlalchemy.schema import UniqueConstraint, PrimaryKeyConstraint
from sqlalchemy.sql.expression import Delete

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
    if table.info['is_distributed']:

        if table.info['distribution_method'] == 'hash':
            distribtion_column = 'partition_key'
            # TODO: What's the optimal shard count and size?
            # This will effect the number of connections on workers, since the
            # coordinator will create a connection for each shard placement.
            shard_count = 10 * cfg.db_nodes
            distribution_column = table.info['distribute_by']
            table = _update_table_constraints(table, distribution_column)
            logger.info(
                'distribute table "%s" by "%s"',
                table.name, distribution_column
            )
            # No replication of tables.
            sql = 'SET citus.shard_replication_factor = 1;\n'
            sql += 'SET citus.shard_count = {n};\n'.format(n=shard_count)
            sql += compiler.visit_create_table(element)
            if table.info['colocate_with'] is not None:
                # NOTE: This would currently fail for "range" distributed tables.
                sql_dist = "'{s}.{t}','{c}','{m}',colocate_with=>'{s}.{t2}'".format(
                    s=table.schema, t=table.name, c=distribution_column,
                    m=table.info['distribution_method'],
                    t2=table.info['colocate_with']
                )
            else:
                sql_dist = "'{s}.{t}','{c}','{m}'".format(
                    s=table.schema, t=table.name, c=distribution_column,
                    m=table.info['distribution_method']
                )
            sql += ';\nSELECT create_distributed_table(%s);\n' % (sql_dist)

        elif table.info['distribution_method'] == 'replication':
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
            raise ValueError(
                'Distribution method "%s" is not supported.'
                % table.info['distribution_method']
            )

    else:
        # Tables don't have to be distributed.
        # If they don't get distributed, they live happily as normal tables
        # on the master node.
        sql = compiler.visit_create_table(element)

    return sql


@compiles(Delete, 'postgresql')
def _compile_delete_elements(construct, compiler, **kwargs):
    sql = compiler.visit_delete(construct, **kwargs)
    if construct.table.info['is_distributed']:
        sql = _compile_distributed_query(sql)
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


def _compile_distributed_query(query):
    '''Compiles a *SQL* query for modification of a hash distributed Citus table.

    Parameters
    ----------
    query: str
        SQL query

    Returns
    -------
    str
        compiled query
    '''
    # This is required for modification of distributed tables
    # TODO: compile DELETE queries
    return '''
        SELECT master_modify_multiple_shards($dist$
            {query}
        $dist$)
    '''.format(query=query)
