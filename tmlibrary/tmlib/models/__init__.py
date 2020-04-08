# TmLibrary - TissueMAPS library for distibuted image analysis routines.
# Copyright (C) 2016-2018 University of Zurich.
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
'''Database models.

A database *model* is an object-relational mapping (ORM) of Python objects
to relational database entries. A class represents a database table, class
attributes correspond to columns of that table and each instances of the class
maps to an individual row of the table.

The central organizational unit of *TissueMAPS* is an
:class:`Experiment <tmlib.models.experiment.Experiment>`. In the database,
each *experiment* is represented by a separate
`schema <https://www.postgresql.org/docs/current/static/ddl-schemas.html>`_,
which contains tables for images and related data.

There is also a *main* (or "public") schema that
holds data beyond the scope of individual *experiments*, such as credentials
of a :class:`User <tmlib.models.user.User>` or the status of a submitted
computational :class:`Task <tmlib.models.submission.Task>`.
The *main* schema further provides reference to existing *experiments*
(see :class:`ExperimentRerefence <tmlib.models.experiment.ExperimentReference>`)
and information on *experiment*-specific user permissions
(see :class:`ExperimentShare <tmlib.models.experiment.ExperimentShare>`).

*Main* and *experiment*-specific database schemas can be accessed
programmatically using :class:`MainSession <tmlib.models.utils.MainSession>` or
:class:`ExperimentSession <tmlib.models.utils.ExperimentSession>`, respectively.
These sessions provide a database transaction that bundles all enclosing
statements into an all-or-nothing operation to ensure that either all or no
changes are persisted in the database. The transaction will be automatically
committed or rolled back in case of an error.
The ``session`` context exposes an instance of
:class:`SQLAlchemySession <tmlib.models.utils.SQLAlchemySession>` and queries
return instances of data model classes derived from
:class:`MainModel <tmlib.models.base.MainModel>` or
:class:`ExperimentModel <tmlib.models.base.ExperimentModel>`, respectively:

.. code-block:: python

    import tmlib.models as tm

    with tm.utils.ExperimentSession(experiment_id=1) as session:
        plates = session.query(tm.Plates).all()
        print(plates)
        print(plates[0].name)
        print(plates[0].acquisitions)

Some *SQL* statements cannot be performed within a transaction. In addition,
the *ORM* comes with a performance overhead and is not optimal for inserting
or updating a large number of rows. In these situations,
:class:`MainConnection <tmlib.models.utils.MainConnection>` or
:class:`ExperimentConnection <tmlib.models.utils.ExperimentConnection>` can
be used. These classes create individual database connections and bypass the
*ORM*. They futher make use of *autocommit* mode, where each statement gets
directly committed such that all changes are immediately effective.
*Sessions* and *connections* are entirely different beasts and expose a
different interface. While *sessions* use the *ORM*, *connections* require
raw *SQL* statements. In addition, they don't return instance of data model
classes, but light-weight instances of a
`namedtuple <https://docs.python.org/2/library/collections.html#collections.namedtuple>`_.
Similar to data models, columns can be accessed via attributes, but the
objects only return the query result without providing any relations to other
objects:

.. code-block:: python

    import tmlib.models as tm

    with tm.utils.ExperimentConnection(experiment_id=1) as connection:
        connection.execute('SELECT * FROM plates;')
        plates = connection.fetchall()
        print(plates)
        print(plates[0].name)

The *session* and *connection* contexts automatically add the
experiment-specific schema to the
`search path <https://www.postgresql.org/docs/current/static/ddl-schemas.html#DDL-SCHEMAS-PATH>`_
at runtime. To access data models outside the scope of a *session* or
*connection*, you either need to set the search path manually or specify the
schema explicitly, e.g. ``SELECT * FROM experiment_1.plates``.

Some of the data models represent distributed table, which are sharded accross
different servers to scale out the database backend over a cluster. To this end,
*TissueMAPS* uses `Citus <https://docs.citusdata.com/en/stable/index.html>`_.
Distributed models are flagged with ``__distribution_method__`` and in case
of *hash* or *range* distribution additionally with ``__distribute_by__``.
This will either replicate the table (so called "reference" table) or
distribute it accross available database server nodes. To this end, the
extension must have been installed on all database servers and these servers
(*worker* nodes) must have been registered on the main database server
(*master* node). For more details on how to set up a database cluster, please
refer to :doc:`installation` section of the documentation.

Distributed tables can be accessed via the *ORM* for reading (``SELECT``) using
:class:`ExperimentSession <tmlib.models.utils.ExperimentSession>`. However,
they cannot be modified (``INSERT``, ``UPDATE`` or ``DELETE``) via the *ORM*,
mainly because multi-statement transactions are not (yet) supported.
Distributed tables must therefore be modified using
:class:`ExperimentConnection <tmlib.models.utils.ExperimentConnection>`.
There are additional *SQL* features that are not supported for distributed
tables. Please refer to the *Citus* documentation for more information on how to
`query <https://docs.citusdata.com/en/latest/dist_tables/querying.html>`_
and `modify <https://docs.citusdata.com/en/latest/dist_tables/dml.html>`_ them.
'''

# NOTE: At the moment we use a separate schema for each experiment and then
# distribute a few selected tables within each schema according to the
# "real-time analytics" model.
# We may want instead a "multi-tenant" model and distribute all tables by hash
# "experiment_id". This would ensure that tables for an experiment would be
# co-localized, which would enable full SQL support:
# https://docs.citusdata.com/en/latest/sharding/data_modeling.html#determining-the-data-model
# https://docs.citusdata.com/en/latest/migration/transitioning.html#transitioning-mt
# https://docs.citusdata.com/en/latest/sharding/colocation.html#table-co-location
# This would, however, result in poorer performance for processing a single
# experiment on the cluster.

from tmlib.models.base import MainModel, ExperimentModel
from tmlib.models.utils import MainSession, ExperimentSession
from tmlib.models.user import User
from tmlib.models.experiment import (
    Experiment, ExperimentReference, ExperimentShare
)
from tmlib.models.well import Well
from tmlib.models.channel import Channel, ChannelLayer
from tmlib.models.tile import ChannelLayerTile
from tmlib.models.mapobject import (
    MapobjectType, Mapobject, MapobjectSegmentation, SegmentationLayer
)
from tmlib.models.feature import Feature, FeatureValues
from tmlib.models.plate import Plate
from tmlib.models.acquisition import Acquisition
from tmlib.models.cycle import Cycle
from tmlib.models.submission import Submission, Task
from tmlib.models.site import Site
from tmlib.models.alignment import SiteShift
from tmlib.models.file import (
    MicroscopeImageFile, MicroscopeMetadataFile, ChannelImageFile,
    IllumstatsFile
)
from tmlib.models.result import (
    ToolResult, LabelValues,
    ScalarToolResult, SupervisedClassifierToolResult,
    SavedSelectionsToolResult, ContinuousToolResult, HeatmapToolResult
)
from tmlib.models.plot import Plot
