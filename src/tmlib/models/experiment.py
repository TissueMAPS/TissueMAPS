import os
import numpy as np
import logging
import itertools
from cached_property import cached_property
from sqlalchemy import Column, String, Integer, Text, ForeignKey
from sqlalchemy.orm import relationship, Session
from sqlalchemy import UniqueConstraint

from tmlib.models import Model, DateMixIn
from tmlib.models.utils import remove_location_upon_delete
from tmlib.models.plate import SUPPORTED_PLATE_FORMATS
from tmlib.models.plate import SUPPORTED_PLATE_AQUISITION_MODES
from tmlib.workflow.metaconfig import SUPPORTED_MICROSCOPE_TYPES
from tmlib.utils import autocreate_directory_property

logger = logging.getLogger(__name__)

#: Format string for experiment locations.
EXPERIMENT_LOCATION_FORMAT = 'experiment_{id}'


@remove_location_upon_delete
class Experiment(Model, DateMixIn):

    '''An *experiment* is the main organizational unit of `TissueMAPS`.
    It represents a set of images and associated data.

    Images are grouped by *plates* and *cycles*. A *plate* represents a
    container for the imaged biological samples and a *cycle* corresponds to a
    particular time point of image acquisition. In the simplest case,
    an *experiment* is composed of a single *plate* with one *cycle* where
    each sample was imaged once.

    Attributes
    ----------
    name: str
        name of the experiment
    root_directory: str
        absolute path to root directory where experiment directory
        should be created in
    description: str
        description of the experimental setup
    stage: str
        currently processed workflow stage
    step: str
        currently processed workflow step
    microscope_type: str
        microscope that was used to acquire the images
    plate_format: int
        number of wells in the plate, e.g. 384
    plate_acquisition_mode: str
        the way plates were acquired with the microscope
    user_id: int
        ID of the owner
    user: tmlib.models.User
        the user who owns the experiment
    plates: List[tmlib.models.Plate]
        plates that belong to the experiment
    channels: List[tmlib.models.Channel]
        channels that belong to the experiment
    mapobject_types: List[tmlib.models.MapobjectType]
        mapobject types that belong to the experiment
    submissions: List[tmlib.models.Submission]
        submissions that belong to the experiment
    zoom_factor: int
        zoom factor between pyramid levels
    vertical_site_displacement: int, optional
        displacement of neighboring sites within a well along the
        vertical axis
    horizontal_site_displacement: int
        displacement of neighboring sites within a well along the
        horizontal axis
    well_spacer_size: int
        gab between neighboring wells in pixels

    See also
    --------
    :py:class:`tmlib.models.Plate`
    :py:class:`tmlib.models.Cycle`
    '''

    #: str: name of the corresponding database table
    __tablename__ = 'experiments'

    __table_args__ = (UniqueConstraint('name', 'user_id'), )

    # Table columns
    name = Column(String)
    microscope_type = Column(String)
    plate_format = Column(Integer)
    plate_acquisition_mode = Column(String)
    description = Column(Text)
    root_directory = Column(String)
    status = Column(String)
    stage = Column(String)
    step = Column(String)
    zoom_factor = Column(Integer)
    vertical_site_displacement = Column(Integer)
    horizontal_site_displacement = Column(Integer)
    well_spacer_size = Column(Integer)
    user_id = Column(Integer, ForeignKey('users.id'), index=True)

    # Relationships to other tables
    user = relationship('User', backref='experiments')

    def __init__(self, name, microscope_type, plate_format,
                 plate_acquisition_mode, user_id,
                 root_directory='$TMAPS_STORAGE', description='',
                 zoom_factor=2, well_spacer_size=500,
                 vertical_site_displacement=0, horizontal_site_displacement=0):
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
        root_directory: str, optional
            absolute path to root directory where experiment directory
            should be created in (default: `$TMAPS_STORAGE`)
        description: str, optional
            description of the experimental setup
        zoom_factor: int, optional
            zoom factor between pyramid levels (default: ``2``)
        well_spacer_size: int
            gab between neighboring wells in pixels (default: ``500``)
        vertical_site_displacement: int, optional
            displacement of neighboring sites within a well along the
            vertical axis (default: ``0``)
        horizontal_site_displacement: int, optional
            displacement of neighboring sites within a well along the
            horizontal axis (default: ``0``)

        See also
        --------
        :py:attr:`tmlib.models.experiment.SUPPORTED_MICROSCOPE_TYPES`
        :py:attr:`tmlib.models.plate.SUPPORTED_PLATE_AQUISITION_MODES`
        :py:attr:`tmlib.models.plate.SUPPORTED_PLATE_FORMATS`
        '''
        self.name = name
        self.user_id = user_id
        self.description = description

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

        self.root_directory = root_directory
        self.status = 'PENDING'  # TODO: get from task table
        self.stage = None
        self.step = None
        self.zoom_factor = zoom_factor
        self.well_spacer_size = well_spacer_size
        # TODO: we may be able to calculate this automatically from OMEXML
        self.vertical_site_displacement = vertical_site_displacement
        self.horizontal_site_displacement = horizontal_site_displacement

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
    def plates_location(self):
        '''str: location where plates data are stored'''
        return os.path.join(self.location, 'plates')

    @autocreate_directory_property
    def channels_location(self):
        '''str: location where channels data are stored'''
        return os.path.join(self.location, 'channels')

    @autocreate_directory_property
    def mapobject_types_location(self):
        '''str: location where mapobject type data are stored'''
        return os.path.join(self.location, 'mapobject_types')

    @autocreate_directory_property
    def workflow_location(self):
        '''str: location where workflow data are stored'''
        return os.path.join(self.location, 'workflow')

    @property
    def session_location(self):
        '''str: location where submission data are stored'''
        return os.path.join(self.workflow_location, 'session')

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
        if (n / np.ceil(np.sqrt(n))) % 2 == 0:
            dimensions = (
                int(np.ceil(np.sqrt(n))), int(n / np.ceil(np.sqrt(n)))
            )
        else:
            dimensions = tuple(np.repeat(int(np.ceil(np.sqrt(n))), 2))
        cooridinates = list(
            itertools.product(
                np.arange(dimensions[0]), np.arange(dimensions[1])
            )
        )
        height, width = dimensions
        grid = np.zeros((height, width), dtype=int)
        for i, c in enumerate(cooridinates):
            if i >= n:
                break
            grid[c[0], c[1]] = self.plates[i].id
        return grid

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

    @property
    def is_ready_for_processing(self):
        '''bool: whether the experiment is ready for processing
        (requires that upload of images is complete)
        '''
        return all([pls.is_ready_for_processing for pls in self.plate_sources])

    def get_mapobject_type(self, name):
        '''
        Return a mapobject type belonging to this experiment by name.

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

    def as_dict(self):
        '''Returns attributes as key-value pairs.

        Returns
        -------
        dict
        '''
        mapobject_info = []
        for t in self.mapobject_types:
            mapobject_info.append({
                'mapobject_type_name': t.name,
                'features': [{'name': f.name} for f in t.features]
            })

        return {
            'id': self.hash,
            'name': self.name,
            'description': self.description,
            'user': self.user.name,
            'plate_format': self.plate_format,
            'microscope_type': self.microscope_type,
            'plate_acquisition_mode': self.plate_acquisition_mode,
            'status': self.status,
            'stage': self.stage,
            'step': self.step,
            'channels': [ch.as_dict() for ch in self.channels],
            'mapobject_info': mapobject_info,
            'plates': [pl.as_dict() for pl in self.plates]
        }

    def __repr__(self):
        return '<Experiment(id=%r, name=%r)>' % (self.id, self.name)
