import logging
from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship

from tmlib.models import Pixels, DateMixIn

logger = logging.getLogger(__name__)


class ChannelImagePixels(Pixels, DateMixIn):

    '''The *pixels* data for a *channel image*.

    Attributes
    ----------
    channel_image_file_id: int
        ID of the parent channel image
    channel_image_file: tmlib.models.ChannelImageFile
        channel image file to which the pixels belongs
    '''

    #: Name of the corresponding database table
    __tablename__ = 'channel_image_pixels'

    # Table columns
    channel_image_file_id = Column(
        Integer, ForeignKey('channel_image_files.id'), primary_key=True
    )

    # Relationship to other tables
    channel_image_file = relationship('ChannelImageFile')
