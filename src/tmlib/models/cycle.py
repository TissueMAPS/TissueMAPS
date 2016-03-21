import os
import logging
from sqlalchemy import Column, String, Integer, ForeignKey
from sqlalchemy.orm import relationship

from tmlib.models import Model
from tmlib.models.utils import auto_remove_directory
from ..utils import autocreate_directory_property

logger = logging.getLogger(__name__)

#: Format string for acquisition locations
CYCLE_LOCATION_FORMAT = 'cycle_{id}'


@auto_remove_directory(lambda obj: obj.location)
class Cycle(Model):

    '''A *cycle* represents an individual image acquisition time point.
    In case of a time series experiment, *cycles* have different time point,
    but the same channel indices, while in case of a "multiplexing"
    experiment, they have the same time point, but different channel indices.

    Attributes
    ----------
    tpoint: int
        time point of the cycle
    status: str
        processing status
    plate_id: int
        ID of the parent plate
    plate: tmlib.models.Plate
        parent plate to which the cycle belongs
    '''

    #: Name of the corresponding database table
    __tablename__ = 'cycles'

    #: Table columns
    tpoint = Column(Integer, index=True)
    status = Column(String)
    plate_id = Column(Integer, ForeignKey('plates.id'))

    #: Relationships to other tables
    plate = relationship('Plate', backref='cycles')

    def __init__(self, tpoint, plate):
        '''
        Parameters
        ----------
        tpoint: int
            time point of the cycle
        plate: tmlib.models.Plate
            parent plate to which the cycle belongs
        '''
        self.tpoint = tpoint
        self.plate_id = plate.id
        self.status = 'WAITING'

    @autocreate_directory_property
    def location(self):
        '''str: location were the acquisition content is stored'''
        if self.id is None:
            raise AttributeError(
                'Cycle "%s" doesn\'t have an entry in the database yet. '
                'Therefore, its location cannot be determined.' % self.name
            )
        return os.path.join(
            self.plate.cycles_location,
            CYCLE_LOCATION_FORMAT.format(id=self.id)
        )

    @autocreate_directory_property
    def channel_images_location(self):
        '''str: location where channel image files are stored'''
        return os.path.join(self.location, 'channel_images')

    @autocreate_directory_property
    def illumstats_location(self):
        '''str: location where illumination statistics files are stored'''
        return os.path.join(self.location, 'illumstats')

    def __repr__(self):
        return '<Cycle(id=%r, tpoint=%r)>' % (self.id, self.tpoint)

    # @property
    # def images(self):
    #     '''
    #     Returns
    #     -------
    #     List[tmlib.image.ChannelImage]
    #         image object for each image file in `image_dir`

    #     Note
    #     ----
    #     Image objects have lazy loading functionality, i.e. the actual image
    #     pixel array is only loaded into memory once the corresponding attribute
    #     (property) is accessed.

    #     Raises
    #     ------
    #     ValueError
    #         when names of image files and names in the image metadata are not
    #         the same
    #     '''
    #     # Get all images
    #     index = xrange(len(self.image_files))
    #     return self.get_image_subset(index)

    # def get_image_subset(self, indices):
    #     '''
    #     Create image objects for a subset of image files in `image_dir`.

    #     Parameters
    #     ----------
    #     indices: List[int]
    #         indices of image files for which an image object should be created

    #     Returns
    #     -------
    #     List[tmlib.image.ChannelImage]
    #         image objects
    #     '''
    #     images = list()
    #     filenames = self.image_metadata.name
    #     # if self.image_files != filenames.tolist():
    #     #     raise ValueError('Names of images do not match')
    #     for i in indices:
    #         f = self.channel_image_files[i]
    #         logger.debug('create image "%s"', f)
    #         image_metadata = ChannelImageMetadata()
    #         table = self.channel_image_metadata[(filenames == f)]
    #         for attr in table:
    #             value = table.iloc[0][attr]
    #             setattr(image_metadata, attr, value)
    #         image_metadata.id = table.index[0]
    #         img = ChannelImage.create_from_file(
    #                 filename=os.path.join(self.image_dir, f),
    #                 metadata=image_metadata)
    #         images.append(img)
    #     return images

    # @property
    # def illumstats_images(self):
    #     '''
    #     Returns
    #     -------
    #     Dict[int, tmlib.image.IllumstatsImages]
    #         illumination statistics images for each channel

    #     Note
    #     ----
    #     Image objects have lazy loading functionality, i.e. the actual image
    #     pixel array is only loaded into memory once the corresponding attribute
    #     is accessed.
    #     '''
    #     illumstats_images = dict()
    #     for c, f in self.illumstats_files.iteritems():
    #         img = IllumstatsImages.create_from_file(
    #                 filename=os.path.join(self.stats_dir, f),
    #                 metadata=self.illumstats_metadata[c])
    #         illumstats_images[c] = img
    #     return illumstats_images
