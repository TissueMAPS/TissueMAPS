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
import os
import logging
import numpy as np
from cached_property import cached_property
from sqlalchemy import Column, String, Integer, Text, ForeignKey
from sqlalchemy.orm import relationship, backref
from sqlalchemy import UniqueConstraint
from sqlalchemy.ext.hybrid import hybrid_property

from tmlib.models.base import DirectoryModel, DateMixIn
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
SUPPORTED_PLATE_AQUISITION_MODES = {'basic', 'multiplexing'}

#: Format string for plate locations
PLATE_LOCATION_FORMAT = 'plate_{id}'


def determine_plate_dimensions(n_wells):
    '''Determines the dimensions of a plate given its number of wells.

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
class Plate(DirectoryModel, DateMixIn):

    '''A *plate* represents a container with reservoirs for biological
    samples (referred to as *wells*).
    It's assumed that all images of a *plate* were acquired with the
    same microscope settings implying that each acquisition has the
    same number of *z-planes* and *channels*.

    The *format* of the plate is encode by the number of wells in the plate,
    e.g. ``384``.

    Note
    ----
    For consistency, a *slide* is considered a single-well *plate*, i.e. a
    *plate* with only one *well*.

    Attributes
    ----------
    acquisitions: List[tmlib.model.Acqusition]
        acquisitions belonging to the plate
    wells: List[tmlib.model.Well]
        wells belonging to the plate
    '''

    __tablename__ = 'plates'

    __table_args__ = (UniqueConstraint('name'), )

    #: str: name given by user
    name = Column(String, index=True)

    #: str: description provided by user
    description = Column(Text)

    #: int: ID of parent experiment
    experiment_id = Column(
        Integer,
        ForeignKey('experiment.id', onupdate='CASCADE', ondelete='CASCADE'),
        index=True
    )

    #: tmlib.models.experiment.Experiment: parent experiment
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
            ID of the parent
            :class:`Experiment <tmlib.models.experiment.Experiment>`
        description: str, optional
            description of the plate
        '''
        self.name = name
        self.description = description
        self.experiment_id = experiment_id

    @hybrid_property
    def location(self):
        '''str: location were the plate is stored'''
        if self._location is None:
            if self.id is None:
                raise AttributeError(
                    'Plate "%s" doesn\'t have an entry in the database yet. '
                    'Therefore, its location cannot be determined.' % self.name
                )
            self._location = os.path.join(
                self.experiment.plates_location,
                PLATE_LOCATION_FORMAT.format(id=self.id)
            )
            if not os.path.exists(self._location):
                logger.debug(
                    'create location for plate "%s": %s',
                    self.name, self._location
                )
                os.mkdir(self._location)
        return self._location

    @location.setter
    def location(self, path_to_files):
        self._location = path_to_files

    @autocreate_directory_property
    def acquisitions_location(self):
        '''str: location where acquisitions are stored'''
        return os.path.join(self.location, 'acquisitions')

    @property
    def status(self):
        '''str: upload status based on the status of acquisitions'''
        child_status = set([f.status for f in self.acquisitions])
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
    def _well_image_size(self):
        well_dims = np.array([w._image_size for w in self.wells])
        if not(len(np.unique(well_dims[:, 0])) == 1 and
                len(np.unique(well_dims[:, 1])) == 1):
            logger.debug('wells don\'t have the same size')
            logger.debug('use size of largest well')
        return (np.max(well_dims[:, 0]), np.max(well_dims[:, 1]))

    @cached_property
    def image_size(self):
        '''Tuple[int]: number of pixels along the vertical and horizontal axis
        '''
        offset = self.experiment.well_spacer_size
        rows = len(self.nonempty_rows)
        cols = len(self.nonempty_columns)
        return (
            rows * self._well_image_size[0] + offset * (rows - 1),
            cols * self._well_image_size[1] + offset * (cols - 1)
        )

    @cached_property
    def offset(self):
        '''Tuple[int]: *y*, *x* coordinate of the top, left corner of the plate
        relative to the layer overview at the maximum zoom level
        '''
        logger.debug('calculate plate offset')
        experiment = self.experiment
        plate_coordinate = zip(*np.where(experiment.plate_grid == self.id))[0]
        y_offset = (
            # Plates above the plate
            plate_coordinate[0] * self.image_size[0] +
            # Gaps introduced between plates
            plate_coordinate[0] * experiment.plate_spacer_size
        )
        x_offset = (
            # Plates left of the plate
            plate_coordinate[1] * self.image_size[1] +
            # Gaps introduced between plates
            plate_coordinate[1] * experiment.plate_spacer_size
        )
        return (y_offset, x_offset)

    def __repr__(self):
        return '<Plate(id=%r, name=%r)>' % (self.id, self.name)
