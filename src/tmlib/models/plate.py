import os
import logging
import numpy as np
from cached_property import cached_property
from sqlalchemy import Column, String, Integer, Text, ForeignKey
from sqlalchemy.orm import relationship

from tmlib.models.base import Model
from tmlib.models.utils import auto_create_directory
from tmlib.models.utils import auto_remove_directory
from ..utils import autocreate_directory_property
# from ..metadata import ImageFileMapping
# from ..readers import JsonReader

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


@auto_remove_directory(lambda obj: obj.location)
@auto_create_directory(lambda obj: obj.location)
class Plate(Model):

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
    '''

    #: Name of the corresponding database table
    __tablename__ = 'plates'

    #: Table columns
    name = Column(String, index=True)
    description = Column(Text)
    status = Column(String)
    experiment_id = Column(Integer, ForeignKey('experiments.id'))

    #: Relationships to other tables
    experiment = relationship('Experiment', backref='plates')

    def __init__(self, name, experiment, description=''):
        '''
        Parameters
        ----------
        name: str
            name of the plate
        experiment: tmlib.experiment.Experiment
            parent experiment to which the plate belongs
        description: str, optional
            description of the plate
        '''
        # TODO: ensure that name is unique within experiment
        self.name = name
        self.description = description
        self.experiment_id = experiment.id
        self.status = 'WAITING'

    @property
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
    def n_wells(self):
        '''int: number of wells in the plate'''
        # TODO: Ensure that this is actually correct!
        return self.experiment.plate_format

    @property
    def dimensions(self):
        '''Tuple[int]: number of wells in the plate along the vertical and
        horizontal axis, i.e. the number of rows and columns
        '''
        return determine_plate_dimensions(self.n_wells)

    @cached_property
    def grid(self):
        '''numpy.ndarray[tmlib.models.Well]: wells arranged according to their
        position within the plate
        '''
        plate_cooridinates = [w.plate_cooridinate for w in self.wells]
        height, width = self.dimensions  # one-based
        grid = np.empty((height, width), dtype=object)
        for i, c in enumerate(plate_cooridinates):
            grid[c[0], c[1]] = self.wells[i]
        return grid

    @property
    def empty_wells_coordinates(self):
        '''List[Tuple[int]]: y, x coordinates of each empty well in the plate,
        i.e. wells that were not imaged
        '''
        empty_wells = np.where(np.logical_not(self.grid))
        coordinates = list()
        for i in xrange(len(empty_wells[0])):
            coordinates.append((empty_wells[0][i], empty_wells[1][i]))
        return coordinates

    @property
    def nonempty_column_indices(self):
        '''List[int]: indices of nonempty columns, i.e. columns of the plate
        where every well has been imaged
        '''
        nonempty_columns = list()
        for i in xrange(self.grid.shape[1]):
            if any(self.grid[:, i]):
                nonempty_columns.append(i)
        return nonempty_columns

    @property
    def nonempty_row_indices(self):
        '''List[int]: indices of nonempty rows, i.e. rows of the plate where
        every well has been imaged
        '''
        nonempty_rows = list()
        for i in xrange(self.grid.shape[0]):
            if any(self.grid[i, :]):
                nonempty_rows.append(i)
        return nonempty_rows

    # @property
    # def image_mapping_file(self):
    #     '''
    #     Returns
    #     -------
    #     str
    #         location of the file that contains the mapping from the
    #         source image files generated by the microscope to the target image
    #         files for the extracted planes
    #     '''
    #     return os.path.join(self.location, 'image_file_mapper.json')

    # @cached_property
    # def image_mapping(self):
    #     '''
    #     Returns
    #     -------
    #     List[tmlib.metadata.ImageFileMapping]
    #         key-value pairs that map the location of individual planes within
    #         the source files to the target files
    #     '''
    #     image_mapping = list()
    #     with JsonReader() as reader:
    #         hashmap = reader.read(self.image_mapping_file)
    #     for element in hashmap:
    #         image_mapping.append(ImageFileMapping(**element))
    #     return image_mapping

    def as_dict(self):
        '''
        Return attributes as key-value pairs.

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
