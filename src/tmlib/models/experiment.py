import os
import numpy as np
import logging
import itertools
from cached_property import cached_property
from sqlalchemy import Column, String, Integer, Text, ForeignKey
from sqlalchemy.orm import relationship, Session
from sqlalchemy import UniqueConstraint

from tmlib.models.base import MainModel, DirectoryModel, DateMixIn
from tmlib.models import ExperimentSession
from tmlib.readers import YamlReader
from tmlib.writers import YamlWriter
from tmlib.models.utils import remove_location_upon_delete
from tmlib.models.plate import SUPPORTED_PLATE_FORMATS
from tmlib.models.plate import SUPPORTED_PLATE_AQUISITION_MODES
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
    name: str
        name given to the experiment
    root_directory: str
        absolute path to root directory where experiment is located on disk
    description: str
        description of the experimental setup
    user_id: int
        ID of the owner
    user: tmlib.models.User
        the user who owns the experiment
    submissions: List[tmlib.models.Submission]
        submissions that belong to the experiment

    See also
    --------
    :py:class:`tmlib.models.Experiment`
    '''

    #: str: name of the corresponding database table
    __tablename__ = 'experiment_references'

    __table_args__ = (UniqueConstraint('name', 'user_id'), )

    # Table columns
    name = Column(String, index=True)
    description = Column(Text)
    root_directory = Column(String)
    user_id = Column(Integer, ForeignKey('users.id'), index=True)

    # Relationships to other tables
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
            ID of the owner
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

    @autocreate_directory_property
    def workflow_location(self):
        '''str: location where workflow data are stored'''
        return os.path.join(self.location, 'workflow')

    @property
    def _workflow_descriptor_file(self):
        return os.path.join(
            self.workflow_location, 'workflow_description.yaml'
        )

    @property
    def workflow_description(self):
        '''tmlib.workflow.tmaps.description.WorkflowDescription: description
        of the workflow

        Raises
        ------
        TypeError
            when description obtained from file is not a mapping
        KeyError
            when description obtained from file doesn't have key "type"

        Note
        ----
        When no description is available from file, a default description is
        provided. The type of the workflow will be determined based on the
        :py:attribute:`tmlib.Experiment.plate_acquisition_mode`.
        '''
        if not os.path.exists(self._workflow_descriptor_file):
            logger.warn('no persistent workflow description found')
            # TODO: we might want to move the workflow description to the
            # actual experiment class or handle it separately.
            with ExperimentSession(self.id) as session:
                exp = session.query(Experiment).get(1)
                if exp.plate_acquisition_mode == 'multiplexing':
                    workflow_type = 'multiplexing'
                else:
                    workflow_type = 'canonical'
            logger.info('default to "%s" workflow type', workflow_type)
            workflow_description = WorkflowDescription(workflow_type)
            self.persist_workflow_description(workflow_description)
        with YamlReader(self._workflow_descriptor_file) as f:
            description = f.read()
        if not isinstance(description, dict):
            raise TypeError('Description must be a mapping.')
        if 'type' not in description:
            raise KeyError('Description must have key "type".')
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
                if step.extra_args is not None:
                    update_choices(step.extra_args)
        return workflow_description

    def persist_workflow_description(self, description):
        '''Persists the workflow description.

        Parameters
        ----------
        description: tmlib.workflow.tmaps.description.WorkflowDescription
            description of the workflow
        '''
        with YamlWriter(self._workflow_descriptor_file) as f:
            f.write(description.as_dict())

    @property
    def session_location(self):
        '''str: location where submission data are stored'''
        return os.path.join(self.workflow_location, 'session')

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

    def __repr__(self):
        return '<ExperimentReference(id=%r, name=%r)>' % (self.id, self.name)


@remove_location_upon_delete
class Experiment(DirectoryModel):

    '''An *experiment* is the main organizational unit of `TissueMAPS`.
    It represents a set of images and associated data.

    Attributes
    ----------
    microscope_type: str
        microscope that was used to acquire the images
    plate_format: int
        number of wells in the plate, e.g. 384
    plate_acquisition_mode: str
        the way plates were acquired with the microscope
    location: str
        absolute path to the location of the experiment on disk
    zoom_factor: int
        zoom factor between pyramid levels
    vertical_site_displacement: int, optional
        displacement of neighboring sites within a well along the
        vertical axis in pixels
    horizontal_site_displacement: int
        displacement of neighboring sites within a well along the
        horizontal axis in pixels
    well_spacer_size: int
        gab between neighboring wells in pixels
    plates: List[tmlib.models.Plate]
        all plates belonging to the experiment
    channels: List[tmlib.models.Channel]
        all channels belonging to the experiment
    mapobject_types: List[tmlib.models.MapobjectType]
        all mapobject types belonging to the experiment
    '''

    __tablename__ = 'experiment'

    microscope_type = Column(String, index=True)
    plate_format = Column(Integer)
    plate_acquisition_mode = Column(String)
    zoom_factor = Column(Integer)
    vertical_site_displacement = Column(Integer)
    horizontal_site_displacement = Column(Integer)
    well_spacer_size = Column(Integer)
    location = Column(String)

    def __init__(self, microscope_type, plate_format, plate_acquisition_mode,
            location, zoom_factor=2, well_spacer_size=500,
            vertical_site_displacement=0, horizontal_site_displacement=0):
        '''
        Parameters
        ----------
        microscope_type: str
            microscope that was used to acquire the images
        plate_format: int
            number of wells in the plate, e.g. 384
        plate_acquisition_mode: str
            the way plates were acquired with the microscope
        location: str
            absolute path to the location of the experiment on disk
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
        :py:attr:`tmlib.workflow.metaconfig.SUPPORTED_MICROSCOPE_TYPES`
        :py:attr:`tmlib.models.plate.SUPPORTED_PLATE_AQUISITION_MODES`
        :py:attr:`tmlib.models.plate.SUPPORTED_PLATE_FORMATS`
        '''
        self.location = location
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

    @autocreate_directory_property
    def plates_location(self):
        '''str: location where plates data are stored'''
        return os.path.join(self.location, 'plates')

    @autocreate_directory_property
    def channels_location(self):
        '''str: location where channels data are stored'''
        return os.path.join(self.location, 'channels')

    @cached_property
    def plate_spacer_size(self):
        '''int: gap between neighboring plates in pixels'''
        return self.well_spacer_size * 2

    @cached_property
    def plate_grid(self):
        '''numpy.ndarray[int]: IDs of plates arranged according to
        their relative position of the plate within the experiment overview
        image
        '''
        n = len(self.plates)
        dimensions = guess_stitch_dimensions(n)
        cooridinates = itertools.product(
            range(dimensions[0]), range(dimensions[1])
        )
        grid = np.zeros(dimensions, dtype=int)
        for i, (y, x) in enumerate(cooridinates):
            grid[y, x] = self.plates[i].id
        return grid
