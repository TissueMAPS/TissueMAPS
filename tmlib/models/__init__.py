'''Database models.

A database `model` is an object-relational mapping (ORM) of Python objects
to database entries. A class represents a database table and class
attributes correspond to columns of that table. Each instances of the class
maps to an individual table entry, i.e. a row.

The central organizational unit of `TissueMAPS` is an
:class:`tmlib.models.experiment.Experiment`. Each `experiment` is represented by
a separate database, which contains the actual images and related data.

There is also a "main" database that holds data beyond the scope of an
individual `experiment`, such as user credentials
(:class:`tmlib.models.user.User`) or the status of submitted computational tasks
(:class:`tmlib.models.submission.Task`). This database further provides
reference to existing `experiment`-specific databases
(:class:`tmlib.models.experiment.ExperimentReference`).

The main and `experiment`-specific databases can accessed and programmatically
using :class:`tmlib.models.utils.MainSession` or
:class:`tmlib.models.utils.ExperimentSession`, respectively. They provide a
database transaction that bundles all enclosing statements into an
all-or-nothing operation to ensure that either all or no changes are persisted.
'''

from tmlib.models.base import MainModel, ExperimentModel
from tmlib.models.utils import MainSession, ExperimentSession
from tmlib.models.user import User
from tmlib.models.experiment import Experiment, ExperimentReference
from tmlib.models.well import Well
from tmlib.models.channel import Channel
from tmlib.models.layer import ChannelLayer
from tmlib.models.tile import ChannelLayerTile
from tmlib.models.mapobject import (
    MapobjectType, Mapobject, MapobjectSegmentation
)
from tmlib.models.feature import Feature, FeatureValue
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
