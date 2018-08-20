# TmLibrary - TissueMAPS library for distibuted image analysis routines.
# Copyright (C) 2016-2018 University of Zurich.
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
import logging
from abc import ABCMeta

from tmlib.utils import assert_type

logger = logging.getLogger(__name__)


class ImageMetadata(object):

    '''Base class for image metadata.'''

    __slots__ = ('_is_aligned', '_is_omitted')

    def __init__(self):
        self.is_aligned = False
        self.is_omitted = False

    @property
    def is_omitted(self):
        '''bool: whether the image should be omitted from further analysis'''
        return self._is_omitted

    @is_omitted.setter
    def is_omitted(self, value):
        if not isinstance(value, bool):
            raise TypeError('Attribute "omit" must have type bool.')
        self._is_omitted = value

    @property
    def is_aligned(self):
        '''bool: whether the image has been aligned between cycles'''
        return self._is_aligned

    @is_aligned.setter
    def is_aligned(self, value):
        if not isinstance(value, bool):
            raise TypeError('Attribute "is_aligned" must have type bool.')
        self._is_aligned = value


class SiteImageMetadata(ImageMetadata):

    '''Base class for metadata of images that map to an individual
    :class:`Site <tmlib.models.site.Site>`.
    '''

    __slots__ = ('_site_id', '_tpoint', '_zplane')

    def __init__(self, site_id, tpoint, zplane):
        '''
        Parameters
        ----------
        site_id: int
            ID of the parent :class:`Site <tmlib.models.site.Site>`
        tpoint: int
            zero-based time point index
        zplane: int
            zero-based z-level index
        '''
        super(SiteImageMetadata, self).__init__()
        self.tpoint = tpoint
        self.zplane = zplane
        self.site_id = site_id

    @property
    def tpoint(self):
        '''int: zero-based time point index'''
        return self._tpoint

    @tpoint.setter
    def tpoint(self, value):
        if not isinstance(value, int):
            raise TypeError('Argument "tpoint" must have type int.')
        self._tpoint = value

    @property
    def zplane(self):
        '''int: zero-based time point index'''
        return self._zplane

    @zplane.setter
    def zplane(self, value):
        if not isinstance(value, int):
            raise TypeError('Argument "zplane" must have type int.')
        self._zplane = value

    @property
    def site_id(self):
        '''int: ID of the corresponding
        :class:`Site <tmlib.models.site.Site>`
        '''
        return self._site_id

    @site_id.setter
    def site_id(self, value):
        if not isinstance(value, int):
            raise TypeError('Argument "site_id" must have type int.')
        self._site_id = value


class SegmentationImageMetadata(SiteImageMetadata):

    '''Metadata for :class:`SegmentationImage <tmlib.image.SegmentationImage>`.
    '''

    __slots__ = ('_mapobject_type_id', )

    def __init__(self, mapobject_type_id, site_id, tpoint, zplane):
        '''
        Parameters
        ----------
        mapobject_type_id: int
            ID of the parent
            :class:`MapobjectType <tmlib.models.mapobject.MapobjectType>`
        site_id: int
            ID of the parent :class:`Site <tmlib.models.site.Site>`
        tpoint: int
            zero-based time point index
        zplane: int
            zero-based z-level index
        '''
        super(SegmentationImageMetadata, self).__init__(site_id, tpoint, zplane)
        self.mapobject_type_id = mapobject_type_id

    @property
    def mapobject_type_id(self):
        '''int: ID of the corresponding
        :class:`MapobjectType <tmlib.models.mapobject.MapobjectType>`
        '''
        return self._mapobject_type_id

    @mapobject_type_id.setter
    def mapobject_type_id(self, value):
        if not isinstance(value, int):
            raise TypeError('Argument "mapobject_type_id" must have type int.')
        self._mapobject_type_id = value

    def __repr__(self):
        return (
            '<%s(mapobject_type_id=%r, site_id=%r, cycle_id=%r, tpoint=%r)' % (
                self.__class__.__name__, self.mapobject_type_id,
                self.site_id, self.cycle_id, self.tpoint
            )
        )


class ChannelImageMetadata(SiteImageMetadata):

    '''Metadata for :class:`ChannelImage <tmlib.image.ChannelImage>`.'''

    __slots__ = (
        '_channel_id', '_cycle_id', '_is_corrected', '_is_rescaled', '_is_clipped',
        '_bottom_residue', '_top_residue',
        '_left_residue', '_right_residue', '_x_shift', '_y_shift'
    )

    def __init__(self, channel_id, site_id, cycle_id, tpoint, zplane):
        '''
        Parameters
        ----------
        channel_id: int
            ID of the parent :class:`Channel <tmlib.models.channel.Channel>`
        site_id: int
            ID of the parent :class:`Site <tmlib.models.site.Site>`
        cycle_id: int
            ID of the parent :class:`Cycle <tmlib.models.cycle.Cycle>`
        tpoint: int
            zero-based time point index
        zplane: int
            zero-based z-level index
        '''
        super(ChannelImageMetadata, self).__init__(site_id, tpoint, zplane)
        self.channel_id = channel_id
        self.cycle_id = cycle_id
        self.is_corrected = False
        self.is_rescaled = False
        self.is_clipped = False
        self.bottom_residue = 0
        self.top_residue = 0
        self.left_residue = 0
        self.right_residue = 0
        self.x_shift = 0
        self.y_shift = 0

    @property
    def channel_id(self):
        '''int: ID of the corresponding
        :class:`Channel <tmlib.models.channel.Channel>`
        '''
        return self._channel_id

    @channel_id.setter
    def channel_id(self, value):
        if not isinstance(value, int):
            raise TypeError('Argument "channel_id" must have type int.')
        self._channel_id = value

    @property
    def cycle_id(self):
        '''int: ID of the corresponding
        :class:`Cycle <tmlib.models.cycle.Cycle>`
        '''
        return self._cycle_id

    @cycle_id.setter
    def cycle_id(self, value):
        if not isinstance(value, int):
            raise TypeError('Argument "cycle_id" must have type int.')
        self._cycle_id = value

    @property
    def bottom_residue(self):
        '''int: excess pixels at the bottom'''
        return self._bottom_residue

    @bottom_residue.setter
    def bottom_residue(self, value):
        if not isinstance(value, int):
            raise TypeError('Attribute "bottom_residue" must have type int')
        self._bottom_residue = value

    @property
    def top_residue(self):
        '''int: excess pixels at the top'''
        return self._top_residue

    @top_residue.setter
    def top_residue(self, value):
        if not isinstance(value, int):
            raise TypeError('Attribute "top_residue" must have type int')
        self._top_residue = value

    @property
    def right_residue(self):
        '''int: excess pixels at the right side'''
        return self._right_residue

    @right_residue.setter
    def right_residue(self, value):
        if not isinstance(value, int):
            raise TypeError('Attribute "right_residue" must have type int')
        self._right_residue = value

    @property
    def left_residue(self):
        '''int: excess pixels at the left side'''
        return self._left_residue

    @left_residue.setter
    def left_residue(self, value):
        if not isinstance(value, int):
            raise TypeError('Attribute "left_residue" must have type int')
        self._left_residue = value

    @property
    def x_shift(self):
        '''int: shift of the image in pixels in x direction relative to the
        site in the reference cycle
        '''
        return self._x_shift

    @x_shift.setter
    def x_shift(self, value):
        if not isinstance(value, int):
            raise TypeError('Attribute "x_shift" must have type int')
        self._x_shift = value

    @property
    def y_shift(self):
        '''int: shift of the image in pixels in y direction relative to the
        site in the reference cycle
        '''
        return self._y_shift

    @y_shift.setter
    def y_shift(self, value):
        if not isinstance(value, int):
            raise TypeError('Attribute "y_shift" must have type int.')
        self._y_shift = value

    @property
    def is_corrected(self):
        '''bool: whether the image is corrected for illumination artifacts'''
        return self._is_corrected

    @is_corrected.setter
    def is_corrected(self, value):
        if not isinstance(value, bool):
            raise TypeError('Attribute "is_corrected" must have type bool')
        self._is_corrected = value

    @property
    def is_clipped(self):
        '''bool: whether the image is clipped'''
        return self._is_clipped

    @is_clipped.setter
    def is_clipped(self, value):
        if not isinstance(value, bool):
            raise TypeError('Attribute "is_clipped" must have type bool')
        self._is_clipped = value

    @property
    def is_rescaled(self):
        '''bool: whether the image is rescaled'''
        return self._is_rescaled

    @is_rescaled.setter
    def is_rescaled(self, value):
        if not isinstance(value, bool):
            raise TypeError('Attribute "is_rescaled" must have type bool')
        self._is_rescaled = value

    def __repr__(self):
        return (
            '<%s(channel_id=%r, site_id=%r, cycle_id=%r, tpoint=%r)' % (
                self.__class__.__name__, self.channel_id,
                self.site_id, self.cycle_id, self.tpoint
            )
        )


class ImageFileMapping(object):

    '''Mapping of 2D pixel planes to original microscope image
    file(s) and the location of individual planes within these files.

    Note
    ----
    The class groups z-planes per :class:`Site <tmlib.models.site.Site>`,
    which is necessary to perform intensity projections.
    '''

    __slots__ = ('_files', '_series', '_planes', '_ref_index')

    def __init__(self, **kwargs):
        '''
        Parameters
        ----------
        kwargs: dict, optional
            file mapping as key-value pairs
        '''
        for key, value in kwargs.iteritems():
            if hasattr(self.__class__, key):
                if isinstance(getattr(self.__class__, key), property):
                    setattr(self, key, value)

    @property
    def files(self):
        '''List[str]: absolute path to the microscope image files'''
        return self._files

    @files.setter
    def files(self, value):
        if not isinstance(value, list):
            raise TypeError('Attribute "files" must have type list')
        if not all([isinstance(v, basestring) for v in value]):
            raise TypeError('Elements of "files" must have type str')
        self._files = value

    @property
    def series(self):
        '''List[int]: zero-based position index of the required series in
        the source file
        '''
        return self._series

    @series.setter
    def series(self, value):
        if not isinstance(value, list):
            raise TypeError('Attribute "series" must have type list')
        if not all([isinstance(v, int) for v in value]):
            raise TypeError('Elements of "series" must have type int')
        self._series = value

    @property
    def planes(self):
        '''List[int]: zero-based position index of the required planes in the
        source file
        '''
        return self._planes

    @planes.setter
    def planes(self, value):
        if not isinstance(value, list):
            raise TypeError('Attribute "planes" must have type list')
        if not all([isinstance(v, int) for v in value]):
            raise TypeError('Elements of "planes" must have type int')
        self._planes = value

    @property
    def ref_index(self):
        '''int: index of the image in the OMEXML *Series*'''
        return self._ref_index

    @ref_index.setter
    def ref_index(self, value):
        if not isinstance(value, int):
            raise TypeError('Attribute "ref_index" must have type int.')
        self._ref_index = value

    def to_dict(self):
        '''Attributes of the class as key-value pairs.

        Returns
        -------
        dict

        Examples
        --------

        >>> ifm = ImageFileMapping()
        >>> ifm.series = [0, 0]
        >>> ifm.planes = [0, 1]
        >>> ifm.files = ["a", "b"]
        >>> ifm.to_dict()
        {'series': [0, 0], 'planes': [0, 1], 'files': ['a', 'b']}

        >>> ifm = ImageFileMapping(series=[0, 0], planes=[0, 1], files=["a", "b"])
        >>> ifm.to_dict()
        {'series': [0, 0], 'planes': [0, 1], 'files': ['a', 'b']}
        '''
        return {
            'files': self.files, 'planes': self.planes, 'series': self.series
        }

    def __repr__(self):
        return '%s(ref_index=%r)' % (self.__class__.__name__, self.ref_index)


class PyramidTileMetadata(object):

    '''Metadata for a :class:`PyramidTile <tmlib.image.PyramidTile>`.'''

    def __init__(self, z, y, x, channel_layer_id):
        '''
        Parameters
        ----------
        z: int
            zero-based zoom level index
        y: int
            zero-based row index
        x: int
            zero-based column index
        channel_layer_id: int
            ID of the parent
            :class:`ChannelLayer <tmlib.models.layer.ChannelLayer>`
        '''
        self.z = z
        self.y = y
        self.x = x
        self.channel_layer_id = channel_layer_id

    def __repr__(self):
        return '%s(z=%r, y=%r, x=%r, channel_layer_id=%r)' % (
            self.__class__.__name__, self.z, self.y, self.x,
            self.channel_layer_id
        )


class IllumstatsImageMetadata(ImageMetadata):

    '''Metadata for an :class:`IllumstatsImage <tmlib.image.IllumstatsImage>`.
    '''

    __slots__ = ('_channel_id', '_is_smoothed')

    def __init__(self, channel_id):
        '''
        Parameters
        ----------
        channel_id: int
            ID of the parent :class:`Channel <tmlib.models.channel.Channel>`
        '''
        super(IllumstatsImageMetadata, self).__init__()
        self.channel_id = channel_id
        self.is_smoothed = False

    @property
    def channel_id(self):
        '''int: ID of the corresponding
        :class:`Channel <tmlib.models.channel.Channel>`
        '''
        return self._channel_id

    @channel_id.setter
    def channel_id(self, value):
        if not isinstance(value, int):
            raise TypeError('Argument "channel_id" must have type int.')
        self._channel_id = value

    @property
    def is_smoothed(self):
        '''bool: whether the illumination statistics image has been smoothed'''
        return self._is_smoothed

    @is_smoothed.setter
    def is_smoothed(self, value):
        if not isinstance(value, bool):
            raise TypeError('Attribute "is_smoothed" must have type bool.')
        self._is_smoothed = value

    def __repr__(self):
        return '%s(channel_id=%r)' % (
            self.__class__.__name__, self.channel_id
        )
