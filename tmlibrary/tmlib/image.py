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
import numpy as np
import scipy.ndimage as ndi
import cv2
import mahotas as mh
import skimage.measure
import skimage.color
import skimage.draw
import shapely.geometry
from geoalchemy2.shape import to_shape
from abc import ABCMeta
import logging

from tmlib.utils import assert_type
from tmlib.metadata import ImageMetadata, PyramidTileMetadata

logger = logging.getLogger(__name__)


class Image(object):

    '''Base class for an image that holds a 2D pixels array.'''

    __slots__ = ('_array', '_metadata')

    def __init__(self, array, metadata=None):
        '''
        Parameters
        ----------
        array: numpy.ndarray
            2D pixels array
        metadata: tmlib.metadata.ImageMetadata, optional
            image metadata (default: ``None``)
        '''
        self.array = array
        self.metadata = metadata

    @property
    def metadata(self):
        '''tmlib.metadata.ImageMetadata: image metadata
        '''
        return self._metadata

    @metadata.setter
    def metadata(self, value):
        if value is not None:
            if not isinstance(value, ImageMetadata):
                raise TypeError(
                    'Argument "metadata" must have type '
                    'tmlib.metadata.ImageMetadata.'
                )
        self._metadata = value

    @property
    def array(self):
        '''numpy.ndarray: 2D pixels array'''
        return self._array

    @array.setter
    def array(self, value):
        if not isinstance(value, np.ndarray):
            raise TypeError(
                'Argument "array" must have type numpy.ndarray.'
            )
        if value.ndim != 2:
            raise ValueError('Argument "array" must be two dimensional.')
        self._array = value

    @property
    def dimensions(self):
        '''Tuple[int]: y, x, z dimensions of the pixels array'''
        return self.array.shape

    @property
    def dtype(self):
        '''str: data type of pixels array elements'''
        return self.array.dtype

    @property
    def is_int(self):
        '''bool: whether pixels array has integer data type
        '''
        return issubclass(self.array.dtype.type, np.integer)

    @property
    def is_float(self):
        '''bool: whether pixels array has float data type
        '''
        return issubclass(self.array.dtype.type, np.float)

    @property
    def is_uint(self):
        '''bool: whether pixels array has unsigned integer data type'''
        return issubclass(self.array.dtype.type, np.unsignedinteger)

    @property
    def is_uint8(self):
        '''bool: whether pixels array has 8-bit unsigned integer data type'''
        return self.array.dtype == np.uint8

    @property
    def is_uint16(self):
        '''bool: whether pixels array has 16-bit unsigned integer data type'''
        return self.array.dtype == np.uint16

    @property
    def is_int32(self):
        '''bool: whether pixels array has 32-bit integer data type'''
        return self.array.dtype == np.int32

    @property
    def is_binary(self):
        '''bool: whether pixels array has boolean data type'''
        return self.array.dtype == np.bool

    def extract(self, y_offset, height, x_offset, width):
        '''Extracts a continuous, rectangular plane of pixels from the image.

        Parameters
        ----------
        y_offset: int
            index of the top, left point of the hyperrectangle on the *y* axis
        height: int
            height of the hyperrectangle, i.e. length of the hyperrectangle
            along the *y* axis
        x_offset: int
            index of the top, left point of the hyperrectangle on the *x* axis
        width: int
            width of the hyperrectangle, i.e. length of the hyperrectangle along
            the *x* axis

        Returns
        -------
        tmlib.image.Image
            extracted image with dimensions `height` x `width`
        '''
        array = self.array[y_offset:(y_offset+height), x_offset:(x_offset+width)]
        return self.__class__(array, self.metadata)

    @assert_type(image='tmlib.image.Image')
    def insert(self, image, y_offset, x_offset, inplace=True):
        '''Inserts a continuous, hyperrectangular volume of pixels into
        an image.

        Parameters
        ----------
        image: tmlib.image.Image
            image whose pixels should be inserted
        y_offset: int
            index of the top, left point of the hyperrectangle on the *y* axis
        x_offset: int
            index of the top, left point of the hyperrectangle on the *x* axis
        inplace: bool, optional
            insert pixels into the existing image rather than into a copy
            (default: ``True``)

        Returns
        -------
        tmlib.image.Image
            modified image
        '''
        if (image.dimensions[0] + y_offset > self.dimensions[0] or
            image.dimensions[1] + x_offset > self.dimensions[1]):
            raise ValueError('Image doesn\'t fit.')
        if inplace:
            array = self.array
        else:
            array = self.array.copy()
        height, width = image.dimensions
        array[y_offset:(y_offset+height), x_offset:(x_offset+width)] = image.array
        if inplace:
            return self
        else:
            return self.__class__(array, self.metadata)

    @assert_type(image='tmlib.image.Image')
    def merge(self, image, axis, offset, inplace=True):
        '''Merges pixels arrays of two images into one.

        Parameters
        ----------
        image: tmlib.image.Image
            image object whose values should used for merging
        axis: str
            axis along which the two images should be merged
            (options: ``{"x", "y"}``)
        offset: int
            offset for `image` in the existing object
        inplace: bool, optional
            merge values into the existing image rather than into a copy
            (default: ``True``)

        Parameters
        ----------
        tmlib.image.Image
            rescaled image
        '''
        if inplace:
            array = self.array
        else:
            array = self.array.copy()
        if axis == 'y':
            array[offset:, :] = image.array[offset:, :]
        elif axis == 'x':
            array[:, offset:] = image.array[:, offset:]
        else:
            raise ValueError('Unknown axis.')
        if inplace:
            return self
        else:
            return self.__class__(array, self.metadata)

    @assert_type(image='tmlib.image.Image')
    def join(self, image, axis):
        '''Joins two pixels arrays.

        Parameters
        ----------
        image: tmlib.image.Image
            image object whose values should be joined
        axis: str
            axis along which the two images should be merged
            (options: ``{"x", "y"}``)

        Returns
        -------
        tmlib.image.Image
            joined image
        '''
        if axis == 'y':
            array = np.vstack([self.array, image.array])
        elif axis == 'x':
            array = np.hstack([self.array, image.array])
        else:
            raise ValueError('Unknown axis.')
        return self.__class__(array, self.metadata)

    def pad_with_background(self, n, side):
        '''Pads one side of the pixels array with zero values.

        Parameters
        ----------
        n: int
            number of pixels that should be added along the given axis
        side: str
            side of the array that should be padded relative to the *y*, *x*
            axis of an individual plane
            (options: ``{"top", "bottom", "left", "right"}``)

        Returns
        -------
        tmlib.image.Image
            padded image
        '''
        height, width = self.dimensions
        if side == 'top':
            array = np.zeros((n, width), dtype=self.dtype)
            array = np.vstack([array, self.array])
        elif side == 'bottom':
            array = np.zeros((n, width), dtype=self.dtype)
            array = np.vstack([self.array, array])
        elif side == 'left':
            array = np.zeros((height, n), dtype=self.dtype)
            array = np.hstack([array, self.array])
        elif side == 'right':
            array = np.zeros((height, n), dtype=self.dtype)
            array = np.hstack([self.array, array])
        else:
            raise ValueError('Unknown side.')
        return self.__class__(array, self.metadata)

    def smooth(self, sigma, inplace=True):
        '''Applies a Gaussian smoothing filter to the pixels array.

        Parameters
        ----------
        sigma: int
            size of the standard deviation of the Gaussian kernel
        inplace: bool, optional
            smooth the array inplace instead of returning a copy
            (default: ``True``)

        Returns
        -------
        tmlib.image.Image
            smoothed image
        '''
        array = mh.gaussian_filter(self.array, sigma)
        if inplace:
            self.array = array
            self.metadata.is_smoothed = True
            return self
        else:
            new_img = self.__class__(array, self.metadata)
            new_img.metadata.is_smoothed = True
            return new_img

    def shrink(self, factor, inplace=True):
        '''Shrinks the first two dimensions of the pixels array
        by `factor`. pixels values of the aggregated array
        are the mean of the neighbouring pixels, where the neighbourhood
        is defined by `factor`.

        Parameters
        ----------
        factor: int
            factor by which the size of the image should be reduced along
            the y and x axis
        inplace: bool, optional
            shrink the array inplace instead of returning a copy
            (default: ``True``)

        Returns
        -------
        tmlib.image.Image
            shrunken image
        '''
        height, width = self.dimensions
        # NOTE: OpenCV uses (x, y) instead of (y, x)
        array = cv2.resize(
            self.array, (width/factor, height/factor),
            interpolation=cv2.INTER_AREA
        )
        if inplace:
            self.array = array
            return self
        else:
            return self.__class__(array, self.metadata)

    @staticmethod
    def _shift_and_crop(img, y, x, bottom, top, right, left, crop=True):
        '''Shifts and crops an image according to the calculated values shift and
        overhang values.

        Parameters
        ----------
        img: numpy.ndarray
            image that should be aligned
        y: int
            shift in y direction (positive value -> down, negative value -> up)
        x: int
            shift in x direction (position value -> right, negative value -> left)
        bottom: int
            pixels to crop at the bottom
        top: int
            pixels to crop at the top
        right: int
            pixels to crop at the right
        left: int
            pixels to crop at the left
        crop: bool, optional
            whether image should cropped or rather padded with zero valued pixels
            (default: ``True``)

        Returns
        -------
        numpy.array
            potentially shifted and cropped image

        Raises
        ------
        IndexError
            when shift or overhang values are too extreme
        '''
        try:
            row_start = top - y
            row_end = bottom + y
            if row_end == 0:
                row_end = img.shape[0]
            else:
                row_end = -row_end
            col_start = left - x
            col_end = right + x
            if col_end == 0:
                col_end = img.shape[1]
            else:
                col_end = -col_end
            if crop:
                aligned_im = img[row_start:row_end, col_start:col_end]
            else:
                aligned_im = np.zeros(img.shape, dtype=img.dtype)
                extracted_im = img[row_start:row_end, col_start:col_end]
                row_end = top + extracted_im.shape[0]
                col_end = left + extracted_im.shape[1]
                aligned_im[top:row_end, left:col_end] = extracted_im
            return aligned_im
        except IndexError as e:
            raise IndexError(
                'Shifting and cropping of the image failed!\n'
                'Shift or residue values are incorrect:\n%s' % str(e)
            )
        except Exception as e:
            raise Exception(
                'Shifting and cropping of the image failed!\n'
                'Reason: %s' % str(e)
            )

    def align(self, crop=True, inplace=True):
        '''Aligns, i.e. shifts and optionally crops, an image based on
        pre-calculated shift and residue values.

        Parameters
        ----------
        crop: bool, optional
            whether image should be cropped or rather padded
            with zero values (default: ``True``)
        inplace: bool, optional
            whether the array of the existing image should be replaced instead
            of creating a copy (default: ``True``)

        Returns
        -------
        tmlib.image.Image
            aligned image

        Warning
        -------
        Alignment may change the dimensions of the image when `crop` is
        ``True``.
        '''
        if self.metadata is None:
            raise AttributeError(
                'Image requires attribute "metadata" for alignment.'
            )
        md = self.metadata
        # The shape of the arrays may change when cropped
        array = self._shift_and_crop(
            self.array, y=md.y_shift, x=md.x_shift,
            bottom=md.bottom_residue, top=md.top_residue,
            right=md.right_residue, left=md.left_residue, crop=crop
        )
        if inplace:
            self.metadata.is_aligned = True
            self.array = array
            return self
        else:
            new_object = self.__class__(array, self.metadata)
            new_object.metadata.is_aligned = True
            return new_object


class ChannelImage(Image):

    '''Class for a channel image: a grayscale image.'''

    def __init__(self, array, metadata=None):
        '''
        Parameters
        ----------
        array: numpy.ndarray[uint16]
            2D pixels array
        metadata: tmlib.metadata.ChannelImageMetadata, optional
            image metadata (note that some methods need to access metadata)
        '''
        super(ChannelImage, self).__init__(array, metadata)
        if not self.is_uint:
            raise TypeError('Image must have unsigned integer type.')

    @property
    def array(self):
        '''numpy.ndarray[numpy.uint16]: 2D pixels array'''
        return self._array

    @array.setter
    def array(self, value):
        if not isinstance(value, np.ndarray):
            raise TypeError(
                'Argument "array" must have type numpy.ndarray.'
            )
        if value.ndim != 2:
            raise ValueError('Argument "array" must be two dimensional.')
        if not(value.dtype == np.uint16 or value.dtype == np.uint8):
            raise ValueError(
                'Argument "array" must have numpy.uint8 or numpy.uint16 data type.'
            )
        self._array = value

    @staticmethod
    def _map_to_uint8(img, lower_bound=None, upper_bound=None):
        '''Maps a 16-bit image trough a lookup table to convert it to 8-bit.

        Parameters
        ----------
        img: numpy.ndarray[np.uint16]
            image that should be mapped
        lower_bound: int, optional
            lower bound of the range that should be mapped to ``[0, 255]``,
            value must be in the range ``[0, 65535]``
            (defaults to ``numpy.min(img)``)
        upper_bound: int, optional
            upper bound of the range that should be mapped to ``[0, 255]``,
            value must be in the range ``[0, 65535]``
            (defaults to ``numpy.max(img)``)

        Returns
        -------
        numpy.ndarray[uint8]
            mapped image
        '''
        if img.dtype != np.uint16:
            raise TypeError('"img" must have 16-bit unsigned integer type.')
        if not(0 <= lower_bound < 2**16) and lower_bound is not None:
                raise ValueError('"lower_bound" must be in the range [0, 65535]')
        if not(0 <= upper_bound < 2**16) and upper_bound is not None:
            raise ValueError('"upper_bound" must be in the range [0, 65535]')
        if lower_bound is None:
            lower_bound = np.min(img)
        if upper_bound is None:
            upper_bound = np.max(img)
        if lower_bound >= upper_bound:
            raise ValueError('"lower_bound" must be smaller than "upper_bound"')
        lut = np.concatenate([
            np.zeros(lower_bound, dtype=np.uint16),
            np.linspace(0, 255, upper_bound - lower_bound).astype(np.uint16),
            np.ones(2**16 - upper_bound, dtype=np.uint16) * 255
        ])
        return lut[img].astype(np.uint8)

    def scale(self, lower, upper, inplace=True):
        '''Scales values to 8-bit such that the range [`lower`, `upper`]
        will be mapped to the range [0, 255].

        Parameters
        ----------
        lower: int
            value below which pixel values will be set to 0
        upper: int
            value above which pixel values will be set to 255
        inplace: bool, optional
            whether values should be rescaled in place rather than creating
            a new image object (default: ``True``)

        Returns
        -------
        tmlib.image.Image
            image with rescaled pixels
        '''
        if self.is_uint16:
            array = self._map_to_uint8(self.array, lower, upper)
            if inplace:
                self.array = array
                self.metadata.is_rescaled = True
                return self
            else:
                new_image = self.__class__(array, self.metadata)
                new_image.metadata.is_rescaled = True
                return new_image
        elif self.is_uint8:
            return self
        else:
            TypeError(
                'Only pixels with unsigned integer type can be scaled.'
            )

    def clip(self, lower, upper, inplace=True):
        '''Clips intensity values below `lower` and above `upper`, i.e. set all
        pixel values below `lower` to `lower` and all above `upper` to `upper`.

        Parameters
        ----------
        lower: int
            value below which pixel values should be clippe
        upper: int
            value above which pixel values should be clipped
        inplace: bool, optional
            whether values should be clipped in place rather than creating
            a new image object (default: ``True``)

        Returns
        -------
        tmlib.image.ChannelImage
            image with clipped pixels
        '''
        array = np.clip(self.array, lower, upper)
        if inplace:
            self.array = array
            self.metadata.is_clipped = True
            return self
        else:
            new_image = self.__class__(array, self.metadata)
            new_image.metadata.is_clipped = True
            return new_image

    @staticmethod
    def _correct_illumination(img, mean, std, log_transform=True):
        '''Corrects an image for illumination artifacts.

        Parameters
        ----------
        img: numpy.ndarray[numpy.uint8 or numpy.uint16]
            image that should be corrected
        mean: numpy.ndarray[numpy.float64]
            matrix of mean values (same dimensions as `img`)
        std: numpy.ndarray[numpy.float64]
            matrix of standard deviation values (same dimensions as `img`)
        log_transform: bool, optional
            log10 transform `img` (default: ``True``)

        Returns
        -------
        numpy.ndarray
            corrected image (same data type as `img`)
        '''
        img_type = img.dtype
        # Do all computations with type float
        img = img.astype(np.float64)
        if log_transform:
            img[img == 0] = 10**-10
            img = np.log10(img)
            img[img == 0] = 0
        img = (img - mean) / std
        img = (img * np.mean(std)) + np.mean(mean)
        if log_transform:
            img = 10 ** img
        # Cast back to original type.
        return img.astype(img_type)

    @assert_type(stats='tmlib.image.IllumstatsContainer')
    def correct(self, stats, inplace=True):
        '''Corrects the image for illumination artifacts.

        Parameters
        ----------
        stats: tmlib.image.IllumstatsContainer
            mean and standard deviation statistics at each pixel position
            calculated over all images of the same channel
        inplace: bool, optional
            whether values should be corrected in place rather than creating
            a new image object (default: ``True``)

        Returns
        -------
        tmlib.image.ChannelImage
            image with pixels corrected for illumination

        Raises
        ------
        ValueError
            when channel doesn't match between illumination statistics and
            image
        '''
        if (stats.mean.metadata.channel_id != self.metadata.channel_id or
                stats.std.metadata.channel_id != self.metadata.channel_id):
            raise ValueError('Channels don\'t match!')
        array = self._correct_illumination(
            self.array, stats.mean.array, stats.std.array
        )
        if inplace:
            self.array = array
            self.metadata.is_corrected = True
            return self
        else:
            new_object = ChannelImage(array, self.metadata)
            new_object.metadata.is_corrected = True
            return new_object

    def png_encode(self):
        '''Encodes pixels of the image in *PNG* format.

        Returns
        -------
        numpy.ndarray[numpy.uint8]
            encoded pixels array

        '''
        logger.info('encode image as PNG')
        return cv2.imencode('.png', self.array)[1]

    def tiff_encode(self):
        '''Encodes pixels of the image in *TIFF* format.

        Returns
        -------
        numpy.ndarray[numpy.uint8]
            encoded pixels array
        '''
        logger.info('encode image as TIFF')
        return cv2.imencode('.tif', self.array)[1]


class SegmentationImage(Image):

    '''Class for a segmentation image: a labeled image where each segmented
    object is encoded by a unique one-based identifier value.

    Warning
    -------
    Pixels values are 32-bit integers. This can create problems when pixels
    should be encoded in *PNG* format. This approach is thus limited to images
    containing less than 65536 objects. *TissueMAPS* doesn't store segmented
    objects in image files, so this limitation only applies to externally
    generated segmentations.
    '''

    def __init__(self, array, metadata=None):
        '''
        Parameters
        ----------
        array: numpy.ndarray[numpy.int32]
            pixels array
        metadata: tmlib.metadata.SegmentationImageMetadata, optional
            image metadata (default: ``None``)
        '''
        super(SegmentationImage, self).__init__(array, metadata)
        if not self.is_int32:
            raise TypeError('Image must have 32-bit integer type.')

    @property
    def array(self):
        '''numpy.ndarray[numpy.int32]: 2D pixels array'''
        return self._array

    @array.setter
    def array(self, value):
        if not isinstance(value, np.ndarray):
            raise TypeError(
                'Argument "array" must have type numpy.ndarray.'
            )
        if value.ndim != 2:
            raise ValueError('Argument "array" must be two dimensional.')
        if not value.dtype == np.int32:
            raise ValueError('Argument "array" must have numpy.int32 data type.')
        self._array = value

    @classmethod
    def create_from_polygons(cls, polygons, y_offset, x_offset, dimensions,
            metadata=None):
        '''Creates an object of class :class:`tmlib.image.SegmentationImage`
        based on coordinates of object contours.

        Parameters
        ----------
        polygons: Tuple[Union[int, geoalchemy2.elements.WKBElement]]
            label and geometry for each segmented object
        y_offset: int
            global vertical offset that needs to be subtracted from
            y-coordinates
        x_offset: int
            global horizontal offset that needs to be subtracted from
            x-coordinates
        dimensions: Tuple[int]
            *x*, *y* dimensions of image *z*-planes that should be created
        metadata: tmlib.metadata.SegmentationImageMetadata, optional
            image metadata (default: ``None``)

        Returns
        -------
        tmlib.image.SegmentationImage
            created image
        '''
        array = np.zeros(dimensions, dtype=np.int32)
        for label, geometry in polygons:
            poly = to_shape(geometry)
            coordinates = np.array(poly.exterior.coords).astype(int)
            x, y = np.split(coordinates, 2, axis=1)
            y *= -1
            x -= x_offset
            y -= y_offset
            y, x = skimage.draw.polygon(y, x, dimensions)
            array[y, x] = label
        return cls(array, metadata)

    def extract_polygons(self, y_offset, x_offset):
        '''Creates a polygon representation for each segmented object.
        The coordinates of the polygon contours are relative to the global map,
        i.e. an offset is added to the :class:`Site <tmlib.models.site.Site>`.

        Parameters
        ----------
        y_offset: int
            global vertical offset that needs to be subtracted from
            *y*-coordinates (*y*-axis is inverted)
        x_offset: int
            global horizontal offset that needs to be added to *x*-coordinates

        Returns
        -------
        Generator[Tuple[Union[int, shapely.geometry.polygon.Polygon]]]
            label and geometry for each segmented object
        '''
        bboxes = mh.labeled.bbox(self.array)
        # We set border pixels to zero to get closed contours for
        # border objects. This may cause problems for very small objects
        # at the border, because they may get lost.
        # We recreate them later on (see below).
        plane = self.array.copy()
        plane[0, :] = 0
        plane[-1, :] = 0
        plane[:, 0] = 0
        plane[:, -1] = 0

        for label in np.unique(plane[plane > 0]):
            bbox = bboxes[label]
            obj_im = self._get_bbox_image(plane, bbox)
            logger.debug('find contour for object #%d', label)
            # We could do this for all objects at once, but doing it on the
            # bounding box for each object individually ensures that we get the
            # correct number of objects and that polygons are in the
            # correct order, i.e. sorted according to their corresponding label.
            mask = obj_im == label
            if np.sum(mask > 0) > 1:
                # We need to remove single pixel extensions on the border of
                # objects because they can lead to polygon self-intersections.
                # However, this should only be done if the object is larger
                # than 1 pixel.
                mask = mh.open(mask)
            # NOTE: OpenCV returns x, y coordinates. This means one would need
            # to flip the axis for numpy-based indexing (y,x coordinates).
            _, contours, hierarchy = cv2.findContours(
                (mask).astype(np.uint8) * 255,
                cv2.RETR_CCOMP,  # two-level hierarchy (holes)
                cv2.CHAIN_APPROX_NONE
            )
            if len(contours) == 0:
                logger.warn('no contours identified for object #%d', label)
                # This is most likely an object that does not extend
                # beyond the line of border pixels.
                # To ensure a correct number of objects we represent
                # it by the smallest possible valid polygon.
                coords = np.array(np.where(plane == label)).T
                y, x = np.mean(coords, axis=0).astype(int)
                shell = np.array([
                    [x-1, x+1, x+1, x-1, x-1],
                    [y-1, y-1, y+1, y+1, y-1]
                ]).T
                holes = None
            elif len(contours) > 1:
                # It may happens that more than one contour is
                # identified per object, for example if the object
                # has holes, i.e. enclosed background pixels.
                logger.debug(
                    '%d contours identified for object #%d',
                    len(contours), label
                )
                holes = list()
                for i in range(len(contours)):
                    child_idx = hierarchy[0][i][2]
                    parent_idx = hierarchy[0][i][3]
                    # There should only be two levels with one
                    # contour each.
                    if parent_idx >= 0:
                        shell = np.squeeze(contours[parent_idx])
                    elif child_idx >= 0:
                        holes.append(np.squeeze(contours[child_idx]))
                    else:
                        # Same hierarchy level. This shouldn't happen.
                        # Take only the largest one.
                        lengths = [len(c) for c in contours]
                        idx = lengths.index(np.max(lengths))
                        shell = np.squeeze(contours[idx])
                        break
            else:
                shell = np.squeeze(contours[0])
                holes = None

            if shell.ndim < 2 or shell.shape[0] < 3:
                logger.warn('polygon doesn\'t have enough coordinates')
                # In case the contour cannot be represented as a
                # valid polygon we create a little square to not loose
                # the object.
                y, x = np.array(mask.shape) / 2
                # Create a closed ring with coordinates sorted
                # counter-clockwise
                shell = np.array([
                    [x-1, x+1, x+1, x-1, x-1],
                    [y-1, y-1, y+1, y+1, y-1]
                ]).T

            # Add offset required due to alignment and cropping and
            # invert the y-axis as required by Openlayers.
            add_y = y_offset + bbox[0] - 1
            add_x = x_offset + bbox[2] - 1
            shell[:, 0] = shell[:, 0] + add_x
            shell[:, 1] = -1 * (shell[:, 1] + add_y)
            if holes is not None:
                for i in range(len(holes)):
                    holes[i][:, 0] = holes[i][:, 0] + add_x
                    holes[i][:, 1] = -1 * (holes[i][:, 1] + add_y)
            poly = shapely.geometry.Polygon(shell, holes)
            if not poly.is_valid:
                logger.warn(
                    'invalid polygon for object #%d - trying to fix it',
                    label
                )
                # In some cases there may be invalid intersections
                # that can be fixed with the buffer trick.
                poly = poly.buffer(0)
                if not poly.is_valid:
                    raise ValueError(
                        'Polygon of object #%d is invalid.' % label
                    )
                if isinstance(poly, shapely.geometry.MultiPolygon):
                    logger.warn(
                        'object #%d has multiple polygons - '
                        'take largest', label
                    )
                    # Repair may create multiple polygons.
                    # We take the largest and discard the smaller ones.
                    areas = [g.area for g in poly.geoms]
                    index = areas.index(np.max(areas))
                    poly = poly.geoms[index]
            yield (int(label), poly)

    @staticmethod
    def _get_bbox_image(img, bbox):
        return np.lib.pad(
            img[bbox[0]:bbox[1], bbox[2]:bbox[3]],
            (1, 1), 'constant', constant_values=(0)
        )


class PyramidTile(Image):

    '''Class for a pyramid tile: an image with a single z-level and
    y, x dimensions of 256 x 256 pixels.
    '''

    TILE_SIZE = 256

    @assert_type(
        metadata=['tmlib.metadata.PyramidTileMetadata', 'types.NoneType']
    )
    def __init__(self, array, metadata=None):
        '''
        Parameters
        ----------
        array: numpy.ndarray[uint8]
            pixels array
        metadata: tmlib.metadata.PyramidTileMetadata, optional
            image metadata (default: ``None``)
        '''
        super(PyramidTile, self).__init__(array, metadata)
        if not self.is_uint8:
            raise TypeError(
                'Image must have 8-bit unsigned integer data type.'
            )
        if any([d > self.TILE_SIZE or d == 0 for d in self.array.shape]):
            raise ValueError(
                'Height and width of image must be greater than zero and '
                'maximally %d pixels.' % self.TILE_SIZE
            )

    @property
    def metadata(self):
        '''tmlib.metadata.ImageMetadata: image metadata
        '''
        return self._metadata

    @metadata.setter
    def metadata(self, value):
        if value is not None:
            if not isinstance(value, PyramidTileMetadata):
                raise TypeError(
                    'Argument "metadata" must have type '
                    'tmlib.metadata.PyramidTileMetadata.'
                )
        self._metadata = value

    @property
    def array(self):
        '''numpy.ndarray[numpy.uint8]: 2D pixels array'''
        return self._array

    @array.setter
    def array(self, value):
        if not isinstance(value, np.ndarray):
            raise TypeError(
                'Argument "array" must have type numpy.ndarray.'
            )
        if value.ndim != 2:
            raise ValueError('Argument "array" must be two dimensional.')
        if not value.dtype == np.uint8:
            raise ValueError(
                'Argument "array" must have numpy.uint8 data type.'
            )
        self._array = value

    @classmethod
    def create_from_binary(cls, string, metadata=None):
        '''Creates an image from a *JPEG* encoded binary string.

        Parameters
        ----------
        string: str
            binary string
        metadata: tmlib.metadata.ImageMetadata, optional
            image metadata (default: ``None``)

        Returns
        -------
        tmlib.image.PyramidTile

        Warning
        -------
        This assumes pixels are encoded as 8-bit unsigned integers.
        '''
        array = np.fromstring(string, np.uint8)
        array = cv2.imdecode(array, cv2.IMREAD_UNCHANGED)
        return cls(array, metadata)

    @classmethod
    def create_from_buffer(cls, buf, metadata=None):
        '''Creates an image from a *JPEG* encoded buffer object.

        Parameters
        ----------
        buf:
            buffer
        metadata: tmlib.metadata.ImageMetadata, optional
            image metadata (default: ``None``)

        Returns
        -------
        tmlib.image.PyramidTile

        Warning
        -------
        This assumes pixels are encoded as 8-bit unsigned integers.
        '''
        array = np.frombuffer(buf, np.uint8)
        array = cv2.imdecode(array, cv2.IMREAD_UNCHANGED)
        return cls(array, metadata)

    @classmethod
    def create_as_background(cls, add_noise=False, mu=None, sigma=None,
            metadata=None):
        '''Creates an image with background pixels. By default background will
        be zero values. Optionally, Gaussian noise can be added to simulate
        camera background.

        Parameters
        ----------
        add_noise: bool, optional
            add Gaussian noise (default: ``False``)
        mu: int, optional
            mean of background noise (default: ``None``)
        sigma: int, optional
            variance of background noise (default: ``None``)
        metadata: tmlib.metadata.ImageMetadata, optional
            image metadata (default: ``None``)

        Returns
        -------
        tmlib.image.PyramidTile
            image with background pixel values
        '''
        if add_noise:
            if mu is None or sigma is None:
                raise ValueError(
                    'Arguments "mu" and "sigma" are required '
                    'when argument "add_noise" is set to True.'
                )
            array = np.random.normal(mu, sigma, cls.TILE_SIZE**2).astype(np.uint8)
        else:
            array = np.zeros((cls.TILE_SIZE,) * 2, dtype=np.uint8)
        return cls(array, metadata)

    def jpeg_encode(self, quality=95):
        '''Encodes the image as a JPEG buffer object.

        Parameters
        ----------
        quality: int, optional
            JPEG quality from 0 to 100 (default: ``95``)

        Returns
        -------
        numpy.ndarray

        Examples
        --------
        >>> img = PyramidTile.create_as_background()
        >>> buf = img.jpeg_encode()
        >>> with open('myfile.jpeg', 'w') as f:
        >>>     f.write(buf)
        '''
        return cv2.imencode(
            '.jpeg', self.array, [cv2.IMWRITE_JPEG_QUALITY, quality]
        )[1]


class IllumstatsImage(Image):

    '''Class for a statistics image: a 2D greyscale image with a
    single band and data type float.
    '''

    @assert_type(
        metadata=['tmlib.metadata.IllumstatsImageMetadata', 'types.NoneType']
    )
    def __init__(self, array, metadata=None):
        '''
        Parameters
        ----------
        array: numpy.ndarray[numpy.float]
            2D pixels array
        metadata: tmlib.metadata.IllumstatsImageMetadata
            metadata (default: ``None``)
        '''
        super(IllumstatsImage, self).__init__(array, metadata)
        if not self.is_float:
            raise TypeError('Image must have data type float.')

    @property
    def array(self):
        '''numpy.ndarray[numpy.float]: 2D pixels array'''
        return self._array

    @array.setter
    def array(self, value):
        if not isinstance(value, np.ndarray):
            raise TypeError(
                'Argument "array" must have type numpy.ndarray.'
            )
        if value.ndim != 2:
            raise ValueError('Argument "array" must be two dimensional.')
        if not value.dtype == np.float:
            raise ValueError(
                'Argument "array" must have numpy.float data type.'
            )
        self._array = value


class IllumstatsContainer(object):

    '''Container for illumination statistics images.

    Provides the mean and standard deviation matrices for a given channel.
    The statistics are calculated at each pixel position over all
    sites acquired in the same channel [1]_.

    References
    ----------
    .. [1] Stoeger T, Battich N, Herrmann MD, Yakimovich Y, Pelkmans L. 2015.
           Computer vision for image-based transcriptomics. Methods.
    '''

    @assert_type(
        mean='tmlib.image.IllumstatsImage', std='tmlib.image.IllumstatsImage'
    )
    def __init__(self, mean, std, percentiles):
        '''
        Parameters
        ----------
        mean: tmlib.image.IllumstatsImage
            mean values at each pixel coordinate calculated over all sites
        std: tmlib.image.IllumstatsImage
            standard deviation values at each pixel coordinate calculated
            over all sites
        percentiles: Dict[float, int]
            intensity percentiles calculated over all sites
        '''
        self.mean = mean
        self.std = std
        self.percentiles = percentiles

    def smooth(self, sigma=5):
        '''Smoothes mean and standard deviation statistic images with a
        Gaussian filter. This is useful to prevent the introduction of
        artifacts upon coorection due to individual outliers pixels with
        extreme values.

        Parameters
        ----------
        sigma: int, optional
            size of the standard deviation of the Gaussian kernel
            (default: ``5``)

        Note
        ----
        :attr:`mean <tmlib.image.IllumstatsImage.mean>` and
        :attr:`std <tmlib.image.IllumstatsImage.std>` are modified in place.
        '''
        self.mean.array = self.mean.smooth(sigma).array
        self.mean.metadata.is_smoothed = True
        self.std.array = self.std.smooth(sigma).array
        self.std.metadata.is_smoothed = True
        return self

    def get_closest_percentile(self, value):
        '''Obtains the value for the percentile closest to a given value.

        Parameters
        ----------
        value: int or float
            approximate percentile value

        Returns
        -------
        int

        Note
        ----
        Necessary due to precision problems with floating-point arithmetic.
        '''
        keys = np.array(self.percentiles.keys())
        idx = np.abs(keys - value).argmin()
        return self.percentiles[keys[idx]]


