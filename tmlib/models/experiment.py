# TmLibrary - TissueMAPS library for distibuted image analysis routines.
# Copyright (C) 2016-2018  University of Zurich
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
import os
import numpy as np
import logging
import itertools
from cached_property import cached_property
from sqlalchemy import Column, String, Integer, Text, ForeignKey, Boolean
from sqlalchemy.orm import relationship, Session
from sqlalchemy import UniqueConstraint

from tmlib.models.base import MainModel, DirectoryModel, DateMixIn
from tmlib.models import ExperimentSession
from tmlib.readers import YamlReader
from tmlib.writers import YamlWriter
from tmlib.models.utils import remove_location_upon_delete
from tmlib.models.plate import SUPPORTED_PLATE_FORMATS
from tmlib.models.plate import SUPPORTED_PLATE_AQUISITION_MODES
from tmlib.workflow.dependencies import get_workflow_type_information
from tmlib.workflow.illuminati.stitch import guess_stitch_dimensions
from tmlib.workflow.description import WorkflowDescription
from tmlib.workflow.metaconfig import SUPPORTED_MICROSCOPE_TYPES
from tmlib.utils import autocreate_directory_property

logger = logging.getLogger(__name__)

#: Format string for experiment locations.
EXPERIMENT_LOCATION_FORMAT = 'experiment_{id}'


@remove_location_upon_delete
class ExperimentReference(MainModel, DateMixIn):

    '''A reference to an *experiment*, which is stored in a separate database.

    All data associated with an experiment are stored in separate,
    experiment-specific databases.

    Attributes
    ----------
    submissions: List[tmlib.models.submission.Submission]
        submissions belonging to the experiment

    See also
    --------
    :class:`tmlib.models.experiment.Experiment`
    '''

    __tablename__ = 'experiment_references'

    __table_args__ = (UniqueConstraint('name', 'user_id'), )

    #: str: name given by the user
    name = Column(String, index=True)

    #: str: description provided by the user
    description = Column(Text)

    #: absolute path to the directory where experiments are located
    root_directory = Column(String)

    #: int: ID of the owner
    user_id = Column(Integer, ForeignKey('users.id'), index=True)

    #: tmlib.models.user.User: user that owns the experiment
    user = relationship('User', back_populates='experiments')

    def __init__(self, name, user_id, root_directory, description=''):
        '''
        Parameters
        ----------
        name: str
            name of the experiment
        microscope_type: str
            microscope that was used to acquire the images
        plate_format: int
            number of wells in the plate, e.g. 384
        plate_acquisition_mode: str
            the way plates were acquired with the microscope
        user_id: int
            ID of the :class:`User <tmlib.models.user.User>` that owns the
            experiment
        root_directory: str
            absolute path to root directory on disk where experiment should
            be created in
        description: str, optional
            description of the experimental setup

        '''
        self.name = name
        self.user_id = user_id
        self.description = description
        self.root_directory = root_directory

    @autocreate_directory_property
    def location(self):
        '''str: location of the experiment,
        e.g. absolute path to a directory on disk
        '''
        if self.id is None:
            raise AttributeError(
                'Experiment "%s" doesn\'t have an entry in the database yet. '
                'Therefore, its location cannot be determined.' % self.name
            )
        return os.path.join(
            os.path.expandvars(self.root_directory),
            EXPERIMENT_LOCATION_FORMAT.format(id=self.id)
        )

    def belongs_to(self, user):
        '''Determines whether the experiment belongs to a given `user`.

        Parameters
        ----------
        user: tmlib.user.User
            `TissueMAPS` user

        Returns
        -------
        bool
            whether experiment belongs to `user`
        '''
        return self.user_id == user.id

    def can_be_accessed_by(self, user_id, permission='write'):
        '''Checks whether a user has the permissions to access the referenced
        experiment.

        Parameters
        ----------
        user_id: int
            ID of :class:`User <tmlib.models.user.User>` for which permissions
            should be checked
        permission: str, optional
            whether user must have ``"read"`` or ``"write"`` permission
            (default: ``"write"``)

        Returns
        -------
        bool
            ``True`` if the user can access the referenced experiment and
            ``False`` otherwise
        '''
        if self.user_id == user_id:
            return True
        else:
            session = Session.object_session(self)
            shares = session.query(ExperimentShare.user_id).\
                filter_by(experiment_id=self.id).\
                all()
            if permission == 'read':
                return user_id in [s.user_id for s in shares]
            elif permission == 'write':
                return user_id in [s.user_id for s in shares if s.write_access]
            else:
                raise ValueError(
                    'Argument "permission" must be either "read" or "write".'
                )

    def __repr__(self):
        return '<ExperimentReference(id=%r, name=%r)>' % (self.id, self.name)


class ExperimentShare(MainModel):

    '''Relationship between a :class:`User <tmlib.models.user.User` and
    an :class:`Experiment <tmlib.models.experiment.ExperimentReference` to
    to share an experiment with other users.

    '''
    __tablename__ = 'experiment_shares'

    __table_args__ = (UniqueConstraint('experiment_id', 'user_id'), )

    #: int: ID of shared experiment
    experiment_id = Column(
        Integer, ForeignKey('experiment_references.id'), index=True
    )

    #: int: ID of user with whom the experiment is shared
    user_id = Column(Integer, ForeignKey('users.id'), index=True)

    #: tmlib.models.experiment.ExperimentReference: shared experiment
    experiment = relationship('ExperimentReference', backref='shares')

    #: tmlib.models.user.User: user with whom the experiment is shared
    user = relationship('User', backref='experiment_shares')

    #: bool: whether the user has write access, i.e. can modify the experiment
    write_access = Column(Boolean, index=True)

    def __init__(self, experiment_id, user_id, write_access=False):
        '''
        Parameters
        ----------
        experiment_id: int
            ID of the :class:`Experiment <tmlib.models.experiment.Experiment>`
            that should be shared
        user_id: int
            ID of the :class:`User <tmlib.models.user.User>` with whom the
            experiment should be shared
        write_access: bool, optional
            whether the user will have write access to the shared experiment
            (default: ``False``)
        '''
        self.experiment_id = experiment_id
        self.user_id = user_id
        self.write_access = write_access


@remove_location_upon_delete
class Experiment(DirectoryModel):

    '''An *experiment* is the main organizational unit of `TissueMAPS`.
    It represents a set of images and associated data.

    Attributes
    ----------
    plates: List[tmlib.models.plate.Plate]
        plates belonging to the experiment
    cycles: List[tmlib.model.cycle.Cycle]
        cycles belonging to the plate
    channels: List[tmlib.models.channel.Channel]
        channels belonging to the experiment
    mapobject_types: List[tmlib.models.mapobject.MapobjectType]
        mapobject types belonging to the experiment
    '''

    __tablename__ = 'experiment'

    #: str: microscope that was used to acquire the images
    microscope_type = Column(String, index=True, nullable=False)

    #: str: workflow type
    workflow_type = Column(String, index=True, nullable=False)

    #: int: number of wells in the plate, e.g. 384
    plate_format = Column(Integer, nullable=False)

    #: str: the order in which plates were acquired via the microscope
    plate_acquisition_mode = Column(String, nullable=False)

    #: int: number of pixels along *y*-axis of the pyramid at highest zoom level
    pyramid_height = Column(Integer)

    #: int: number of pixels along *x*-axis of the pyramid at highest zoom level
    pyramid_width = Column(Integer)

    #: int: number of zoom levels of the pyramid
    pyramid_depth = Column(Integer)

    #: int: zoom factor between pyramid levels
    zoom_factor = Column(Integer, nullable=False)

    #: displacement of neighboring sites within a well along the
    #: vertical axis in pixels
    vertical_site_displacement = Column(Integer, nullable=False)

    #: displacement of neighboring sites within a well along the
    #: horizontal axis in pixels
    horizontal_site_displacement = Column(Integer, nullable=False)

    #: int: gap introduced between neighbooring wells in pixels
    well_spacer_size = Column(Integer, nullable=False)

    def __init__(self, id, microscope_type, plate_format, plate_acquisition_mode,
            location, workflow_type='canonical', zoom_factor=2,
            well_spacer_size=500, vertical_site_displacement=0,
            horizontal_site_displacement=0):
        '''
        Parameters
        ----------
        id: int
            ID that should be assigned to the experiment
        microscope_type: str
            microscope that was used to acquire the images
        plate_format: int
            number of wells in the plate, e.g. 384
        plate_acquisition_mode: str
            the way plates were acquired with the microscope
        location: str
            absolute path to the location of the experiment on disk
        workflow_type: str, optional
            name of an implemented workflow type (default: ``"canonical"``)
        zoom_factor: int, optional
            zoom factor between pyramid levels (default: ``2``)
        well_spacer_size: int
            gab between neighboring wells in pixels (default: ``500``)
        vertical_site_displacement: int, optional
            displacement of neighboring sites within a well along the
            vertical axis in pixels (default: ``0``)
        horizontal_site_displacement: int, optional
            displacement of neighboring sites within a well along the
            horizontal axis in pixels (default: ``0``)

        See also
        --------
        :attr:`tmlib.workflow.metaconfig.SUPPORTED_MICROSCOPE_TYPES`
        :attr:`tmlib.models.plate.SUPPORTED_PLATE_AQUISITION_MODES`
        :attr:`tmlib.models.plate.SUPPORTED_PLATE_FORMATS`
        '''
        self.id = id
        self._location = location
        self.zoom_factor = zoom_factor
        self.well_spacer_size = well_spacer_size
        # TODO: we may be able to calculate this automatically from OMEXML
        self.vertical_site_displacement = vertical_site_displacement
        self.horizontal_site_displacement = horizontal_site_displacement
        if microscope_type not in SUPPORTED_MICROSCOPE_TYPES:
            raise ValueError(
                'Unsupported microscope type! Supported are: "%s"'
                % '", "'.join(SUPPORTED_MICROSCOPE_TYPES)
            )
        self.microscope_type = microscope_type

        if plate_format not in SUPPORTED_PLATE_FORMATS:
            raise ValueError(
                'Unsupported plate format! Supported are: %s'
                % ', '.join(map(str, SUPPORTED_PLATE_FORMATS))
            )
        self.plate_format = plate_format

        if plate_acquisition_mode not in SUPPORTED_PLATE_AQUISITION_MODES:
            raise ValueError(
                'Unsupported acquisition mode! Supported are: "%s"'
                % '", "'.join(SUPPORTED_PLATE_AQUISITION_MODES)
            )
        self.plate_acquisition_mode = plate_acquisition_mode

        implemented_workflow_types = get_workflow_type_information()
        if workflow_type not in implemented_workflow_types:
            raise ValueError(
                'Unsupported workflow type! Supported are: "%s"'
                % '", "'.join(implemented_workflow_types)
            )
        self.workflow_type = workflow_type

    @property
    def location(self):
        '''str: location of the experiment'''
        return self._location

    @autocreate_directory_property
    def plates_location(self):
        '''str: location where plates data are stored'''
        return os.path.join(self.location, 'plates')

    @autocreate_directory_property
    def channels_location(self):
        '''str: location where channel data are stored'''
        return os.path.join(self.location, 'channels')

    @cached_property
    def plate_spacer_size(self):
        '''int: gap between neighboring plates in pixels'''
        return self.well_spacer_size * 2

    @cached_property
    def plate_grid(self):
        '''numpy.ndarray[int]: IDs of plates arranged according to
        their relative position of the plate within the experiment overview
        image (sorted row-wise by plate names)
        '''
        n = len(self.plates)
        dimensions = guess_stitch_dimensions(n)
        cooridinates = itertools.product(
            range(dimensions[1]), range(dimensions[0])
        )
        grid = np.zeros(dimensions, dtype=int)
        plates = sorted(self.plates, key=lambda p: p.id)
        for i, (x, y) in enumerate(cooridinates):
            try:
                grid[y, x] = plates[i].id
            except IndexError:
                continue
        return grid

    @autocreate_directory_property
    def workflow_location(self):
        '''str: location where workflow data are stored'''
        return os.path.join(self.location, 'workflow')

    @autocreate_directory_property
    def tools_location(self):
        '''str: location where tool data are stored'''
        return os.path.join(self.location, 'tools')

    @property
    def _workflow_descriptor_file(self):
        return os.path.join(
            self.workflow_location, 'workflow_description.yaml'
        )

    @property
    def workflow_description(self):
        '''tmlib.workflow.tmaps.description.WorkflowDescription: description
        of the workflow

        Note
        ----
        When no description is available from file, a default description is
        provided. The type of the workflow will be determined based on
        :attr:`workflow_type <tmlib.models.experiment.Experiment.workflow_type>`.
        '''
        if not os.path.exists(self._workflow_descriptor_file):
            logger.warn('no persistent workflow description found')
            with ExperimentSession(self.id) as session:
                exp = session.query(Experiment).get(self.id)
                workflow_type = exp.workflow_type
            logger.info('create workflow of type "%s"', workflow_type)
            workflow_description = WorkflowDescription(workflow_type)
            self.persist_workflow_description(workflow_description)

        with YamlReader(self._workflow_descriptor_file) as f:
            description = f.read()
        if not isinstance(description, dict):
            raise TypeError('Description must be a mapping.')
        if 'type' not in description:
            raise KeyError('Workflow description must have key "type".')
        if 'stages' not in description:
            raise KeyError('Workflow description must have key "stages".')

        workflow_description = WorkflowDescription(**description)
        def update_choices(arguments):
            for arg in arguments.iterargs():
                if getattr(arg, 'get_choices', None):
                    arg.choices = arg.get_choices(self)

        for stage in workflow_description.stages:
            for step in stage.steps:
                update_choices(step.batch_args)
                update_choices(step.submission_args)

        return workflow_description

    def persist_workflow_description(self, description):
        '''Persists the workflow description and updates `workflow_type`.

        Parameters
        ----------
        description: tmlib.workflow.tmaps.description.WorkflowDescription
            description of the workflow
        '''
        self.workflow_type = description.type
        with YamlWriter(self._workflow_descriptor_file) as f:
            f.write(description.to_dict())

    def get_mapobject_type(self, name):
        '''Returns a mapobject type belonging to this experiment by name.

        Parameters
        ----------
        name : str
            the name of the mapobject_type to be returned

        Returns
        -------
        tmlib.models.MapobjectType

        Raises
        ------
        sqlalchemy.orm.exc.MultipleResultsFound
           when multiple mapobject types with this name were found
        sqlalchemy.orm.exc.NoResultFound
           when no mapobject type with this name was found

        '''
        from tmlib.models import MapobjectType
        session = Session.object_session(self)
        return session.query(MapobjectType).\
            filter_by(name=name, experiment_id=self.id).\
            one()
