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
import re
import logging
import numpy as np
import pandas as pd
import sys
import traceback
import bioformats
from natsort import natsorted
import collections
from abc import ABCMeta
from abc import abstractmethod

from tmlib.metadata import ImageFileMapping
from tmlib.workflow.illuminati import stitch
from tmlib.errors import MetadataError
from tmlib.errors import RegexError
from tmlib.errors import NotSupportedError
from tmlib.workflow.metaconfig.omexml import XML_DECLARATION

logger = logging.getLogger(__name__)


_SUPPORTED__FIELDS = {'w', 'c', 'z', 't', 's'}


_FIELD_DEFAULTS = {'w': 'A01', 'c': '1', 'z': 0, 't': 0, 's': 0}


MetadataFields = collections.namedtuple(
    'MetadataFields', list(_SUPPORTED__FIELDS)
)


class MetadataHandler(object):

    '''Abstract base class for handling metadata from
    heterogeneous microscope file formats as provided by the
    `Bio-Formats <http://www.openmicroscopy.org/site/products/bio-formats>`_
    library.

    Metadata has to be provided as *OMEXML* according to the
    `OME schema <http://www.openmicroscopy.org/Schemas/Documentation/Generated/OME-2015-01/ome.html>`_.

    Attributes
    ----------
    metadata: pandas.DataFrame
        configured metadata
    '''

    __metaclass__ = ABCMeta

    @classmethod
    def check_regular_expression(cls, regex):
        '''Checks whether a named regular expression has all required fields.

        Parameters
        ----------
        regex: str
            regular expression

        Raises
        ------
        tmlib.erros.RegexError
            when a provided field is not supported
        '''
        if not regex:
            raise RegexError('No regular expression provided.')
        provided_fields = re.findall(r'\(\?P\<(\w+)\>', regex)
        for name in provided_fields:
            if name not in _SUPPORTED__FIELDS:
                raise RegexError(
                    '"%s" is not a supported regular expression field.\n'
                    'Supported are "%s"'
                    % (name, '", "'.join(_SUPPORTED__FIELDS))
                )

        for name in _SUPPORTED__FIELDS:
            if name not in provided_fields and name in _FIELD_DEFAULTS:
                logger.warning(
                    'regular expression field "%s" not provided, defaults to %s',
                    name, str(_FIELD_DEFAULTS[name])
                )

    @classmethod
    def extract_fields_from_filename(cls, regex, filename, defaults=True):
        '''Extracts fields from image filenames using a regular expression.

        Parameters
        ----------
        regex: str
            regular expression
        filename: str
            name of a microscope image file
        defaults: bool, optional
            whether default values should be used

        Returns
        -------
        tmlib.workflow.metaconfig.base.MetadataFields
            named tuple with extracted values
        '''
        r = re.compile(regex)
        match = r.search(str(filename))
        if match is None:
            raise RegexError(
                'Metadata attributes could not be retrieved from '
                'filename "%s" using regular expression "%s"' % (
                    filename, regex
                )
            )
        captures = match.groupdict()
        for k in _SUPPORTED__FIELDS:
            v = captures.get(k, None)
            if v is None:
                if defaults:
                    captures[k] = str(_FIELD_DEFAULTS[k])
                else:
                    captures[k] = v
        return MetadataFields(**captures)

    def __init__(self, omexml_images, omexml_metadata=None):
        '''
        Parameters
        ----------
        omexml_images: Dict[str, bioformats.omexml.OMEXML]
            name and extracted metadata for each
            :class:`MicroscopeImageFile <tmlib.models.file.MicroscopeImageFile>`
        omexml_metadata: bioformats.omexml.OMEXML, optional
            additional metadata obtained from additional
            :class:`MicroscopeMetadataFile <tmlib.modles.file.MicroscopeMetdataFile>`
            via a microscope type specific implementation of
            :class:`MetdataReader <tmlib.workflow.metaconfig.base.MetadataReader>`
        '''
        logger.info('instantiate metadata handler')
        for name, md in omexml_images.iteritems():
            if not isinstance(md, bioformats.omexml.OMEXML):
                raise TypeError(
                    'Value of "%s" of argument "omexml_images" must '
                    'have type bioformats.omexml.OMEXL.' % name
                )
        self._file_mapper_list = list()
        self._file_mapper_lut = collections.defaultdict(list)
        self._omexml = self._combine_omexml_elements(
            omexml_images, omexml_metadata
        )
        self._filenames = natsorted(omexml_images)
        self.metadata = pd.DataFrame()

    @staticmethod
    def _create_channel_planes(pixels):
        # Add new *Plane* elements to an existing OMEXML *Pixels* object.
        n_channels = pixels.SizeC
        n_stacks = pixels.SizeZ
        n_timepoints = pixels.SizeT
        pixels.plane_count = n_channels * n_stacks * n_timepoints

        channel_position = pixels.DimensionOrder.index('C')
        stack_position = pixels.DimensionOrder.index('Z')
        time_position = pixels.DimensionOrder.index('T')

        sorted_attributes = sorted([
            (channel_position, 'TheC'),
            (stack_position, 'TheZ'),
            (time_position, 'TheT')
        ])

        sorted_counts = sorted([
            (channel_position, n_channels),
            (stack_position, n_stacks),
            (time_position, n_stacks)
        ])

        count = 0
        for i in xrange(sorted_counts[0][1]):
            for j in xrange(sorted_counts[1][1]):
                for k in xrange(sorted_counts[2][1]):
                    setattr(pixels.Plane(count), sorted_attributes[0][1], i)
                    setattr(pixels.Plane(count), sorted_attributes[1][1], j)
                    setattr(pixels.Plane(count), sorted_attributes[2][1], k)
                    count += 1

        return pixels

    def configure_from_omexml(self):
        '''Collects image metadata from *OMEXML* elements extracted form
        image files and an additional optional *OMEXML* element provided by
        a microscope-specific implementation of
        :class:`MetadataReader <tmlib.workflow.metaconfig.base.MetadataReader>`.
        All all available metadata gets combined into a table, where each row
        represents a single 2D pixels plane.

        Returns
        -------
        pandas.DataFrame
            metadata for each 2D *Plane* element

        Note
        ----
        An original image file may contain more than one *Image* element,
        which is referred to as a *Series*.
        Each *Image*/*Pixels* element contains at least one *Plane* element.
        A *Plane* represents a 2-dimensional pixel array for a given channel,
        z-resolution and time point. The different planes are often grouped
        together as a *Series* per acquisition site, i.e. microscope stage
        position.
        The actual structure of the image dataset, i.e. the distribution of
        images across files, is highly variable and microscope dependent.

        In TissueMAPS, each *Plane* is stored in a separate file.
        This is advantageous, because it makes it easy
        for libraries to read the contained pixel array without the need for
        specialized readers and prevents problems with parallel I/O.
        '''
        logger.info('configure metadata from OMEXML')

        def get_bit_depth(pixel_type):
            r = re.compile(r'(\d+)$')
            m = r.search(pixel_type)
            if not m:
                raise RegexError(
                    'Bit depth could not be determined from pixel type.'
                )
            return int(m.group(1))

        metadata = collections.defaultdict(list)
        for i in xrange(self._omexml.image_count):
            image = self._omexml.image(i)
            # It is assumed that all *Plane* elements where
            # acquired at the same site, i.e. microscope stage position.
            pixels = image.Pixels

            bit_depth = get_bit_depth(image.Pixels.PixelType)

            n_planes = pixels.plane_count
            metadata['bit_depth'].extend([bit_depth for _ in range(n_planes)])
            for p in xrange(n_planes):
                plane = pixels.Plane(p)

                metadata['name'].append(image.Name)

                channel = pixels.Channel(plane.TheC)
                metadata['channel_name'].append(channel.Name)

                metadata['tpoint'].append(plane.TheT)
                metadata['zplane'].append(plane.TheZ)

                metadata['date'].append(image.AcquisitionDate)

                metadata['height'].append(pixels.SizeY)
                metadata['width'].append(pixels.SizeX)

                metadata['stage_position_y'].append(plane.PositionY)
                metadata['stage_position_x'].append(plane.PositionX)

        self.metadata = pd.DataFrame(metadata)
        length = self.metadata.shape[0]
        self.metadata['well_name'] = np.empty((length, ), dtype=str)
        self.metadata['well_position_y'] = np.empty((length, ), dtype=int)
        self.metadata['well_position_x'] = np.empty((length, ), dtype=int)
        self.metadata['site'] = np.empty((length, ), dtype=int)

        if len(self._omexml.plates) == 0:
            logger.warn('OMEXML does not specify a Plate element')
        else:
            plate = self._omexml.plates[0]
            for w in plate.Well:
                well = plate.Well[w]
                n_samples = len(well.Sample)
                for s in xrange(n_samples):
                    image_index = well.Sample[s].ImageRef
                    for p in xrange(n_planes):
                        index = image_index + image_index * (n_planes - 1) + p
                        self.metadata.at[index, 'well_name'] = str(w)

        return self.metadata

    def _combine_omexml_elements(self, omexml_images, omexml_metadata):
        logger.info('combine OMEXML elements')
        # We assume here that each image files contains the same number images.
        n_images = omexml_images.values()[0].image_count * len(omexml_images)
        if omexml_metadata is not None:
            extra_omexml_available = True
            if not isinstance(omexml_metadata, bioformats.omexml.OMEXML):
                raise TypeError(
                    'Argument "omexml_metadata" must have type '
                    'bioformats.omexml.OMEXML.'
                )
            if omexml_metadata.image_count != n_images:
                raise MetadataError(
                    'Number of images in "omexml_metadata" must match '
                    'the total number of Image elements in "omexml_images".'
                )
        else:
            extra_omexml_available = False
            omexml_metadata = bioformats.OMEXML(XML_DECLARATION)
            omexml_metadata.image_count = n_images

        image_element_attributes = {'AcquisitionDate', 'Name'}
        channel_element_attributes = {'Name'}
        pixel_element_attributes = {
            'PixelType', 'SizeC', 'SizeT', 'SizeX', 'SizeY', 'SizeZ'
        }
        plane_element_attributes = {
            'PositionX', 'PositionY', 'PositionZ', 'TheC', 'TheT', 'TheZ'
        }
        filenames = natsorted(omexml_images)
        count = 0
        for i, f in enumerate(filenames):
            omexml_img = omexml_images[f]
            n_series = omexml_img.image_count
            for s in xrange(n_series):
                extracted_image = omexml_img.image(s)
                md_image = omexml_metadata.image(count)
                for attr in image_element_attributes:
                    extracted_value = getattr(extracted_image, attr)
                    if extracted_value is not None:
                        setattr(md_image, attr, extracted_value)

                extracted_pixels = extracted_image.Pixels
                n_planes = extracted_pixels.plane_count
                if n_planes == 0:
                    # Sometimes an image doesn't have any plane elements.
                    # Let's create them for consistency.
                    extracted_pixels = self._create_channel_planes(extracted_pixels)
                    n_planes = extracted_pixels.plane_count

                md_pixels = md_image.Pixels
                md_pixels.plane_count = n_planes
                if extra_omexml_available and (md_pixels.plane_count != n_planes):
                    raise MetadataError(
                        'Image element #%d in OMEXML obtained from additional '
                        'metdata files must have the same number of Plane  '
                        'elements as the corresponding Image elements in the '
                        'OMEXML element obtained from image file "%s".' % (i, f)
                    )

                for attr in pixel_element_attributes:
                    extracted_value = getattr(extracted_pixels, attr)
                    if extracted_value is not None:
                        # This is python-bioformats being stupid by setting
                        # random default values.
                        setattr(md_pixels, attr, extracted_value)

                for p in xrange(n_planes):
                    extracted_plane = extracted_pixels.Plane(p)
                    md_plane = md_pixels.Plane(p)
                    for attr in plane_element_attributes:
                        extracted_value = getattr(extracted_plane, attr)
                        md_value = getattr(md_plane, attr)
                        if md_value is None and extracted_value is not None:
                            setattr(md_plane, attr, extracted_value)

                    fm = ImageFileMapping()
                    fm.ref_index = count + p
                    fm.files = [f]
                    fm.series = [s]
                    fm.planes = [p]
                    self._file_mapper_list.append(fm)
                    self._file_mapper_lut[f].append(fm)

                n_channels = extracted_pixels.channel_count
                md_image.channel_count = n_channels
                for c in xrange(n_channels):
                    extracted_channel = extracted_pixels.Channel(c)
                    md_channel = md_pixels.Channel(c)
                    for attr in channel_element_attributes:
                        extracted_value = getattr(extracted_channel, attr)
                        if extracted_value is not None:
                            setattr(md_channel, attr, extracted_value)

                count += 1

        return omexml_metadata

    def determine_missing_metadata(self):
        '''Determines if required basic metadata information, such as
        channel names or time point identifiers, could not yet been configured.

        Returns
        -------
        Set[str]
            names of missing basic metadata attributes
        '''
        logger.info('check whether required metadata information is missing')
        md = self.metadata
        missing_metadata = set()
        if any([len(v) < 3 for v in md.well_name.values]):
            missing_metadata.add('well')
        if any(md.channel_name.isnull()):
            missing_metadata.add('channel')
        if any(md.zplane.isnull()):
            missing_metadata.add('focal plane')
        if any(md.tpoint.isnull()):
            missing_metadata.add('time point')
        return missing_metadata

    def configure_from_filenames(self, plate_dimensions, regex):
        '''Configures metadata based on information encoded in image filenames
        using a regular expression with the followsing fields:

            - *w*: well
            - *t*: time point
            - *s*: acquisition site
            - *z*: focal plane (z dimension)
            - *c*: channel

        Parameters
        ----------
        plate_dimensions: Tuple[int]
            number of rows and columns in the well plate
        regex: str
            named regular expression

        Raises
        ------
        tmlib.errors.MetadataError
            when image files contain more than more plane, since this case
            wouldn't allow a 1-to-1 mapping of information from filename to
            image plane

        Returns
        -------
        pandas.DataFrame
            metadata for each 2D *Plane* element
        '''
        logger.info('update image metadata with filename information')
        md = self.metadata
        filenames = natsorted(list(set([
            f for fm in self._file_mapper_list for f in fm.files
        ])))
        if md.shape[0] != len(filenames):
            raise MetadataError(
                'Configuration of metadata based on filenames '
                'works only when each image file contains only a single plane.'
            )

        logger.info('retrieve metadata from filenames via regular expression')
        self.check_regular_expression(regex)
        for i, f in enumerate(filenames):
            # Not every microscope provides all the information in the filename.
            fields = self.extract_fields_from_filename(regex, f)
            md.at[i, 'channel_name'] = str(fields.c)
            md.at[i, 'site'] = int(fields.s)
            md.at[i, 'zplane'] = int(fields.z)
            md.at[i, 'tpoint'] = int(fields.t)
            md.at[i, 'well_name'] = str(fields.w)

        return self.metadata

    @staticmethod
    def _calculate_coordinates(positions, n):
        return stitch.calc_grid_coordinates_from_positions(positions, n)

    def determine_grid_coordinates_from_stage_positions(self):
        '''Determines the coordinates of each image acquisition site within the
        continuous acquisition grid (slide or well in a plate)
        based on the absolute microscope stage positions.

        Returns
        -------
        pandas.DataFrame
            metadata for each 2D *Plane* element

        Raises
        ------
        MetadataError
            when stage position information is not available from `metadata`

        See also
        --------
        :func:`illuminati.stitch.calc_grid_coordinates_from_positions`
        '''
        md = self.metadata
        if (any(md.stage_position_y.isnull()) or
                any(md.stage_position_x.isnull())):
                raise MetadataError(
                    'Stage position information is not available.'
                )

        logger.info(
            'translate absolute microscope stage positions into '
            'relative acquisition grid coordinates'
        )

        planes_per_well = md.groupby(['well_name'])
        n_tpoints = len(np.unique(md.tpoint))
        n_channels = len(np.unique(md.channel_name))
        n_zplanes = len(np.unique(md.zplane))
        for well_name in np.unique(md.well_name):
            ix = planes_per_well.groups[well_name]
            positions = zip(
                md.loc[ix, 'stage_position_y'],
                md.loc[ix, 'stage_position_x']
            )
            n = len(positions) / (n_tpoints * n_channels * n_zplanes)
            coordinates = self._calculate_coordinates(positions, n)
            md.loc[ix, 'well_position_y'] = [c[0] for c in coordinates]
            md.loc[ix, 'well_position_x'] = [c[1] for c in coordinates]

        return self.metadata

    def determine_grid_coordinates_from_layout(self, stitch_layout,
            stitch_dimensions):
        '''Determines the coordinates of each image acquisition site within the
        continuous acquisition grid (slide or well in a plate)
        based on a provided layout.

        Parameters
        ----------
        stitch_layout: str
            layout of the acquisition grid
            (options: ``"horizontal"``, ``"zigzag_horizontal"``, ``"vertical"``,
            or ``"zigzag_vertical"``)
        stitch_dimensions: Tuple[int]
            dimensions of the acquisition grid, i.e. number of images
            along the vertical and horizontal axis of the acquired area

        Returns
        -------
        pandas.DataFrame
            metadata for each 2D *Plane* element

        See also
        --------
        :func:`illuminati.stitch.calc_grid_coordinates_from_layout`
        '''
        md = self.metadata

        logger.info('determine acquisition grid coordinates based on layout')
        # Determine the number of unique positions per well
        acquisitions_per_well = md.groupby([
            'well_name', 'channel_name', 'zplane', 'tpoint'
        ])
        n_acquisitions_per_well = acquisitions_per_well.count().name
        if len(np.unique(n_acquisitions_per_well)) > 1:
            raise MetadataError(
                'Each well must have the same number of acquisition sites.'
            )
        n_sites = n_acquisitions_per_well[0]
        sites = acquisitions_per_well.groups.values()

        logger.debug(
            'stitch layout: {0}; stitch dimensions: {1}'.format(
            stitch_layout, stitch_dimensions)
        )
        coordinates = stitch.calc_grid_coordinates_from_layout(
            stitch_dimensions, stitch_layout
        )
        y_coordinates = [c[0] for c in coordinates]
        x_coordinates = [c[1] for c in coordinates]
        for indices in sites:
            if len(indices) != len(coordinates):
                raise ValueError('Incorrect stitch dimensions provided.')
            md.loc[indices, 'well_position_y'] = y_coordinates
            md.loc[indices, 'well_position_x'] = x_coordinates

        return self.metadata

    def group_metadata_per_zstack(self):
        '''Group all focal planes belonging to one z-stack (i.e. acquired
        at different z resolutions but at the same microscope stage position,
        time point and channel) together.

        Returns
        -------
        pandas.DataFrame
            metadata for each 2D *Plane* element
        '''
        md = self.metadata

        logger.info('group metadata per z-stack')
        zstacks = md.groupby([
            'well_name', 'well_position_x', 'well_position_y',
            'channel_name', 'tpoint'
        ])
        logger.debug('identified %d z-stacks', zstacks.ngroups)

        # Map the locations of each plane with the original image files
        # in order to be able to perform the intensity projection later on
        grouped_file_mapper_list = list()
        grouped_file_mapper_lut = collections.defaultdict(list)
        rows_to_drop = list()
        for key, indices in zstacks.groups.iteritems():
            fm = ImageFileMapping()
            fm.files = list()
            fm.series = list()
            fm.planes = list()
            fm.ref_index = indices[0]
            for index in indices:
                fm.files.extend(self._file_mapper_list[index].files)
                fm.series.extend(self._file_mapper_list[index].series)
                fm.planes.extend(self._file_mapper_list[index].planes)
            grouped_file_mapper_list.append(fm)
            grouped_file_mapper_lut[tuple(fm.files)].append(fm)
            # Keep only the first record
            rows_to_drop.extend(indices[1:])

        # Update metadata and file mapper objects
        self.metadata.drop(self.metadata.index[rows_to_drop], inplace=True)
        self._file_mapper_list = grouped_file_mapper_list
        self._file_mapper_lut =  grouped_file_mapper_lut

        return self.metadata

    def update_indices(self):
        '''Creates for each channel, time point and z-plane a zero-based
        unique identifier number.

        Returns
        -------
        pandas.DataFrame
            metadata for each 2D *Plane* element

        Warning
        -------
        Apply this method only at the end of the configuration process.
        '''
        logger.info('update channel index')
        md = self.metadata
        channels = np.unique(md.channel_name)
        for i, c in enumerate(channels):
            md.loc[(md.channel_name == c), 'channel'] = i
        md.channel = md.channel.astype(int)
        tpoints = np.unique(md.tpoint)
        for i, t in enumerate(tpoints):
            md.loc[(md.tpoint == t), 'tpoint'] = i
        zplanes = np.unique(md.zplane)
        for i, z in enumerate(zplanes):
            md.loc[(md.zplane == z), 'zplane'] = i
        return self.metadata

    def assign_acquisition_site_indices(self):
        '''Gives each acquisition site a globally (plate-wide) unique index.

        Returns
        -------
        pandas.DataFrame
            metadata for each 2D *Plane* element
        '''
        logger.info('assign plate wide acquisition site indices')
        md = self.metadata
        sites = md.groupby(['well_name', 'well_position_x', 'well_position_y'])
        site_indices = sorted(sites.groups.values(), key=lambda k: k[0])
        for i, indices in enumerate(site_indices):
            md.loc[indices, 'site'] = i
        md.site = md.site.astype(int)
        return self.metadata

    def remove_redundant_columns(self):
        '''Cleans up metadata, i.e. remove information that is no longer required.

        Returns
        -------
        pandas.DataFrame
            metadata for each 2D *Plane* element
        '''
        logger.info('remove redundant metadata')
        logger.debug('remove column "stage_position_y"')
        del self.metadata['stage_position_y']
        logger.debug('remove column "stage_position_x"')
        del self.metadata['stage_position_x']

        return self.metadata

    def create_image_file_mappings(self):
        '''Creates a file map for the extraction of individual planes from the
        microscopy image files.

        Returns
        -------
        Dict[int, Dict[str, List[str or int]]]
            a mapping of configured images hashable by their index in `metadata`
            to planes in the corresponding microscope image files
            (*files* key) and their location within the files
            (*series* and *plane* keys)
        '''
        logger.info('build image file mappings')
        md = self.metadata
        mapper = dict()
        for item in self._file_mapper_list:
            mapper[item.ref_index] = item.to_dict()
        return mapper


class MetadataReader(object):

    '''Abstract base class for reading metadata from additional non-image
    files, which are either generated by the microscope or provided by users.

    The ``read()`` method of derived classes must return a single *OMEXML*
    object, according to the OME data model, see
    `python-bioformats <http://pythonhosted.org/python-bioformats/#metadata>`.
    The value of the *image_count* attribute in the *OMEXML* element provided
    by the implemented reader must equal the number of image files * the number
    of *Image* elements per file * number of *Plane* elements per *Image*
    element. In addition, the number of *Plane* elements and the values of
    *SizeT*, *SizeC* and *SizeZ* elements of the *Image* element must match
    those in *OMEXML* elements obtained from the corresponding image files.
    For example, if an image file contains one series with planes for one time
    point, one channel and 10 focal planes, then
    *SizeT* = 1, *SizeC* = 1 and *SizeZ* = 10.

    The OME schema doesn't provide information about wells at the individual
    *Image* level: see `OME data model <http://www.openmicroscopy.org/Schemas/Documentation/Generated/OME-2015-01/ome.html>`_.
    Instead, it provides a *Plate* element, which contains *Well* elements.
    *Well* elements contain the positional information, such as row and
    column index of each well within the plate. *WellSample* elements map to
    to individual *Image* elements and hold information about the position
    of images within the *Well*. In addition, there is an *ImageRef* element,
    which can be used to map the *WellSample* to its corresponding *Image*
    element.

    Derived classes should provide information for the SPW *Plate* element.
    For consistency, a slide should be represented as a *Plate* with a single
    *Well* element. Custom readers should futher specify the *ImageRef* element
    for each *WellSample* element.
    The value of *ImageRef* must be an unsigned integer in the range [0, *n*],
    where *n* is the total number of *Image* elements in the *OMEXML* element
    provided by the class.
    Individual *Image* elements may be distributed accross several *OMEXML*
    elements (one *OMEXML* element for each
    :class:`MicroscopeImageFile <tmlib.models.file.MicroscopeImageFile>`). The
    *ImageRef* value for a particular *Image* can be calculated as follows:
    one-based index in the naturally sorted list of image filenames * number
    of *Image* elements per image file.

    See also
    --------
    :meth:`tmlib.workflow.metaconfig.base.MetadataHandler.configure_omexml_from_image_files`
    :meth:`tmlib.workflow.metaconfig.base.MetadataHandler.configure_omexml_from_metadata_files`
    '''

    __metaclass__ = ABCMeta

    def __enter__(self):
        return self

    def __exit__(self, except_type, except_value, except_trace):
        if except_value:
            sys.stdout.write(
                'The following error occurred while reading from file:\n%s'
                % str(except_value)
            )
            for tb in traceback.format_tb(except_trace):
                sys.stdout.write(tb)
            sys.exit(1)

    @abstractmethod
    def read(self, microscope_metadata_files, microscope_image_files):
        '''Reads metadata from arbitrary files.

        Parameters
        ----------
        microscope_metadata_files: List[str]
            absolute path to the microscope metadata files
        microscope_image_files: List[str]
            absolute path to the microscope image files

        Returns
        -------
        bioformats.omexml.OMEXML
            OMEXML metadata
        '''
        pass
