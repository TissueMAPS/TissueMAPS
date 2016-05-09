import os
import logging
import numpy as np
from cached_property import cached_property
from sqlalchemy import Column, String, Integer, Text, ForeignKey
from sqlalchemy.orm import relationship, backref
from sqlalchemy import UniqueConstraint

from tmlib.models.base import Model, DateMixIn
from tmlib.models.utils import remove_location_upon_delete
from tmlib.models.status import FileUploadStatus as fus
from tmlib.utils import autocreate_directory_property

logger = logging.getLogger(__name__)

#: Supported plate formats (number of wells in the plate).
SUPPORTED_PLATE_FORMATS = {1, 96, 384}

#: Supported plate acquisition modes. Mode "series" means that *cycles*
#: are interpreted as separate acquisitions relating to the same marker
#: as part of a time series experiment.
#: Mode "multiplexing" implies that a different marker was used in each
#: acquisition as part of a multiplexing experiment.
SUPPORTED_PLATE_AQUISITION_MODES = {'time_series', 'multiplexing'}

#: Format string for plate locations
PLATE_LOCATION_FORMAT = 'plate_{id}'


def determine_plate_dimensions(n_wells):
    '''Determine the dimensions of a plate given its number of wells.

    Parameters
    ----------
    n_wells: int
        number of wells in the plate

    Returns
    -------
    Tuple[int]
        number of rows and column in the plate
    '''
    plate_dimensions = {
        1:   (1, 1),
        96:  (8, 12),
        384: (16, 24)
    }
    return plate_dimensions[n_wells]


@remove_location_upon_delete
class Plate(Model, DateMixIn):

    '''A *plate* represents a container with reservoirs for biological
    samples (*wells*).
    It's assumed that the imaged area projected onto the x, y plane of the
    *well* bottom is continuous and the same for all *wells* in the *plate*.
    It's further assumed that all images of a *plate* were acquired with the
    same microscope settings implying that each acquisition (*cycle*) has the
    same number of *z-planes* and *channels*.

    The *format* of the plate is encode by the number of wells in the plate,
    e.g. ``384``.

    Note
    ----
    For consistency, a *slide* is considered a single-well *plate*, i.e. a
    *plate* with only one *well*.

    Attributes
    ----------
    name: str
        name of the plate
    description: str, optional
        description of the plate
    experiment_id: int
        ID of the parent experiment
    experiment: tmlib.experiment.Experiment
        parent experiment to which the plate belongs
    cycles: List[tmlib.model.Cycle]
        cycles that belong to the plate
    acquisitions: List[tmlib.model.Acqusition]
        acquisitions that belong to the plate
    wells: List[tmlib.model.Well]
        wells that belong to the plate
    '''

    #: str: name of the corresponding database table
    __tablename__ = 'plates'

    __table_args__ = (UniqueConstraint('name', 'experiment_id'), )

    # Table columns
    name = Column(String, index=True)
    description = Column(Text)
    experiment_id = Column(
        Integer, ForeignKey(
            'experiments.id', onupdate='CASCADE', ondelete='CASCADE'
        )
    )

    # Relationships to other tables
    experiment = relationship(
        'Experiment',
        backref=backref('plates', cascade='all, delete-orphan')
    )

    def __init__(self, name, experiment_id, description=''):
        '''
        Parameters
        ----------
        name: str
            name of the plate
        experiment_id: int
            ID of the parent experiment
        description: str, optional
            description of the plate
        '''
        self.name = name
        self.description = description
        self.experiment_id = experiment_id

    @autocreate_directory_property
    def location(self):
        '''str: location were the plate content is stored'''
        if self.id is None:
            raise AttributeError(
                'Plate "%s" doesn\'t have an entry in the database yet. '
                'Therefore, its location cannot be determined.' % self.name
            )
        return os.path.join(
            self.experiment.plates_location,
            PLATE_LOCATION_FORMAT.format(id=self.id)
        )

    @autocreate_directory_property
    def acquisitions_location(self):
        '''str: location where acquisitions are stored'''
        return os.path.join(self.location, 'acquisitions')

    @autocreate_directory_property
    def cycles_location(self):
        '''str: location where cycles are stored'''
        return os.path.join(self.location, 'cycles')

    @property
    def status(self):
        '''str: upload status based on the status of acquisitions'''
        child_status = set([
            f.status for f in self.acquisitions
        ])
        if fus.UPLOADING in child_status:
            return fus.UPLOADING
        elif len(child_status) == 1 and fus.COMPLETE in child_status:
            return fus.COMPLETE
        else:
            return fus.WAITING

    @property
    def n_wells(self):
        '''int: number of wells in the plate'''
        return self.experiment.plate_format

    @property
    def dimensions(self):
        '''Tuple[int]: number of wells in the plate along the vertical and
        horizontal axis, i.e. the number of rows and columns
        '''
        return determine_plate_dimensions(self.n_wells)

    @cached_property
    def well_grid(self):
        '''numpy.ndarray[int]: IDs of wells arranged according to their
        relative position within the plate
        '''
        height, width = self.dimensions
        grid = np.zeros((height, width), dtype=int)
        for w in self.wells:
            grid[w.y, w.x] = w.id
        return grid

    @cached_property
    def _empty_wells_coordinates(self):
        '''List[Tuple[int]]: y, x coordinates of each empty wells in the plate,
        i.e. wells that were not imaged
        '''
        empty_wells = np.where(np.logical_not(self.well_grid))
        coordinates = list()
        for i in xrange(len(empty_wells[0])):
            coordinates.append((empty_wells[0][i], empty_wells[1][i]))
        return coordinates

    @cached_property
    def nonempty_columns(self):
        '''List[int]: indices of nonempty columns, i.e. columns of the plate
        where at least one well has been imaged
        '''
        nonempty_columns = list()
        for i in xrange(self.well_grid.shape[1]):
            if any(self.well_grid[:, i]):
                nonempty_columns.append(i)
        return nonempty_columns

    @cached_property
    def nonempty_rows(self):
        '''List[int]: indices of nonempty rows, i.e. rows of the plate where
        at least one well has been imaged
        '''
        nonempty_rows = list()
        for i in xrange(self.well_grid.shape[0]):
            if any(self.well_grid[i, :]):
                nonempty_rows.append(i)
        return nonempty_rows

    @cached_property
    def image_size(self):
        '''Tuple[int]: number of pixels along the vertical and horizontal axis

        Warning
        -------
        It's assumed that all wells have the same size.
        '''
        if len(self.wells) == 0:
            return None
        offset = self.experiment.well_spacer_size
        if len(self.wells) == 0:
            return None
        well_dims = np.array([w.image_size for w in self.wells])
        if not(len(np.unique(well_dims[:, 0])) == 1 and
                len(np.unique(well_dims[:, 1])) == 1):
            logger.warning('wells don\'t have equal sizes')
        well_size = (np.max(well_dims[:, 0]), np.max(well_dims[:, 1]))
        rows = len(self.nonempty_rows)
        cols = len(self.nonempty_columns)
        return (
            rows * well_size[0] + offset * (rows - 1),
            cols * well_size[1] + offset * (cols - 1)
        )

    @cached_property
    def offset(self):
        '''Tuple[int]: *y*, *x* coordinate of the top, left corner of the plate
        relative to the layer overview at the maximum zoom level
        '''
        experiment = self.experiment
        plate_coordinate = tuple(
            [a[0] for a in np.where(experiment.plate_grid == self.id)]
        )
        y_offset = (
            # Plates above the plate
            plate_coordinate[0] * self.image_size[0] +
            # Gaps introduced between plates
            plate_coordinate[0] * experiment.plate_spacer_size
        )
        x_offset = (
            # Plates left of the plate
            plate_coordinate[1] * self.image_size[0] +
            # Gaps introduced between plates
            plate_coordinate[1] * experiment.plate_spacer_size
        )
        return (y_offset, x_offset)

    def belongs_to(self, user):
        '''Determines whether the plate belongs to a given `user`.

        Parameters
        ----------
        user: tmlib.user.User
            `TissueMAPS` user

        Returns
        -------
        bool
            whether plate belongs to `user`
        '''
        return self.experiment.user_id == user.id

    def as_dict(self):
        '''Returns attributes as key-value pairs.

        Returns
        -------
        dict
        '''
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'status': self.status,
            'acquisitions': [aq.as_dict() for aq in self.acquisitions]
        }

    def __repr__(self):
        return '<Plate(id=%r, name=%r)>' % (self.id, self.name)
