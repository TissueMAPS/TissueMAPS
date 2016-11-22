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
'''Database models.

A database `model` is an object-relational mapping (ORM) of Python objects
to database entries. A class represents a database table and class
attributes correspond to columns of that table. Each instances of the class
maps to an individual table entry, i.e. a row.

The central organizational unit of `TissueMAPS` is an
:class:`Experiment <tmlib.models.experiment.Experiment>`. Each `experiment`
is represented by a separate database
`schema <https://www.postgresql.org/docs/current/static/ddl-schemas.html>`_,
which contains the actual images and related data.

There is also a "main" schema (its actually the "public" schema) that
holds data beyond the scope of an individual *experiment*, such as credentials
of a :class:`User <tmlib.models.user.User>`) or the status of a submitted
computational :class:`Task <tmlib.models.submission.Task>`.
This schema further provides reference to existing *experiment*-specific
database schemas
(see :class:`ExperimentRerefence <tmlib.models.experiment.ExperimentReference>`)
and information on *experiment*-specific user permissions
(see :class:`ExperimentShare <tmlib.models.experiment.ExperimentShare>`).

*Main* and *experiment*-specific databases schemas can accessed programmatically
using :class:`MainSession <tmlib.models.utils.MainSession>` or
:class:`ExperimentSession <tmlib.models.utils.ExperimentSession>`, respectively.
These sessions provide a database transaction that bundles all enclosing
statements into an all-or-nothing operation to ensure that either all or no
changes are persisted in the database.

Some of the data models can be distributed, i.e. the tables can be shared.
To this end, *TissueMAPS* uses
`Citus <https://docs.citusdata.com/en/stable/index.html>`_, a
`PostgreSQL extension <https://www.postgresql.org/docs/current/static/extend-extensions.html>`_.
These models are flagged with either ``__distribute_by_replication__`` or
``__distribute_by_hash__``, which will either replicate the table
(so called "reference" tables) or distributed it accross all available nodes
of the database cluster. Table distribution is implemented in form of a
`SQLAlchemy dialect <>`_ named ``citus``. To active it, set
:attr:`db_driver <tmlib.config.DefaultConfig.db_driver>` configuration
variable to ``citus``. Note, however, that the extension must have been
installed and nodes activated. More more details refer to :mod:`tmsetup`.

The *ORM* is convient and easy to use. This convenience comes at a cost:
performance. For performance-critical operations (in particular large number
of inserts), we therfore rely on
`bulk operations <http://docs.sqlalchemy.org/en/latest/orm/persistence_techniques.html#bulk-operations>`_,
which bypass most of the *ORM* functionality.

'''

from tmlib.models.base import MainModel, ExperimentModel
from tmlib.models.utils import MainSession, ExperimentSession
from tmlib.models.user import User
from tmlib.models.experiment import (
    Experiment, ExperimentReference, ExperimentShare
)
from tmlib.models.well import Well
from tmlib.models.channel import Channel
from tmlib.models.layer import (
    ChannelLayer, LabelLayer, ScalarLabelLayer, SupervisedClassifierLabelLayer,
    ContinuousLabelLayer, HeatmapLabelLayer
)
from tmlib.models.tile import ChannelLayerTile
from tmlib.models.mapobject import (
    MapobjectType, Mapobject, MapobjectSegmentation
)
from tmlib.models.feature import Feature, FeatureValue, LabelValue
from tmlib.models.plate import Plate
from tmlib.models.acquisition import Acquisition, ImageFileMapping
from tmlib.models.cycle import Cycle
from tmlib.models.submission import Submission, Task
from tmlib.models.site import Site
from tmlib.models.alignment import SiteShift, SiteIntersection
from tmlib.models.file import (
    MicroscopeImageFile, MicroscopeMetadataFile, ChannelImageFile,
    IllumstatsFile
)
from tmlib.models.result import ToolResult
from tmlib.models.plot import Plot
