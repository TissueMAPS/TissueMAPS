import os
import re
import logging
import numpy as np
import pandas as pd
import sys
import traceback
from natsort import natsorted
from collections import defaultdict
from collections import OrderedDict
from abc import ABCMeta
from abc import abstractmethod

from tmlib.metadata import ImageFileMapping
from tmlib.workflow.illuminati import stitch
from tmlib.errors import MetadataError
from tmlib.errors import RegexError
from tmlib.errors import NotSupportedError

logger = logging.getLogger(__name__)


class MetadataHandler(object):

    '''Abstract base class for handling metadata from
    heterogeneous microscope file formats as provided by the
    `Bio-Formats <http://www.openmicroscopy.org/site/products/bio-formats>`_
    library.

    Metadata has to be available as OMEXML according to the
    `OME schema <http://www.openmicroscopy.org/Schemas/Documentation/Generated/OME-2015-01/ome.html>`_.

    Attributes
    ----------
    omexml_images: Dict[str, bioformats.omexml.OMEXML]
        name and OMEXML metadata for each microscope image file
    omexml_metadata: bioformats.omexml.OMEXML
        OMEXML metadata generated based on microscope metadata files
    metadata: pandas.DataFrame
        configured metadata
    '''

    __metaclass__ = ABCMeta

    def __init__(self, omexml_images, omexml_metadata):
        '''
        Parameters
        ----------
        omexml_images: Dict[str, bioformats.omexml.OMEXML]
            name and OMEXML metadata for each microscope image file
        omexml_metadata: bioformats.omexml.OMEXML, optional
            OMEXML metadata generated based on microscope metadata files
        '''
        self.omexml_images = omexml_images
        self.omexml_metadata = omexml_metadata
        self.metadata = pd.DataFrame()
        self._file_mapper_list = list()
        self._file_mapper_lookup = defaultdict(list)
        self._wells = dict()

    @staticmethod
    def _create_channel_planes(pixels):
        '''Adds new `Plane` elements to an existing OMEXML `Pixels` element for
        each channel, z-plane or time point.

        Parameters
        ----------
        pixels: bioformats.OMEXML.Image.Pixels
            pixels element to which new planes should be added
        '''
        # Add new *Plane* elements to an existing OMEXML *Pixels* object,
        # such that z-stacks are grouped by channel.
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

    def configure_omexml_from_image_files(self):
        '''Collects image metadata from individual `OMEXML` elements (one for each
        original image file) and combine them into a metadata table, where each
        row represents a single-plane image elements.

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

        In TissueMAPS, each *Plane* representing a unique combination of
        channel, time point and z-resolution is ultimately stored in a
        separate file. This is advantageous, because it makes it easy
        for libraries to read the contained pixel array without the need for
        specialized readers and prevents problems with parallel I/O on
        the cluster.
        '''
        logger.info('configure OMEXML metadata extracted from image files')
        i = 0
        # NOTE: The order of files is important for some metadata information!
        filenames = natsorted(self.omexml_images.keys())

        def get_bit_depth(pixel_type):
            r = re.compile(r'(\d+)$')
            m = r.search(pixel_type)
            if not m:
                raise RegexError(
                    'Bit depth could not be determined from pixel type.'
                )
            return int(m.group(1))

        metadata = OrderedDict()
        metadata['name'] = list()
        metadata['channel_name'] = list()
        metadata['tpoint'] = list()
        metadata['zplane'] = list()
        metadata['bit_depth'] = list()
        metadata['stage_position_y'] = list()
        metadata['stage_position_x'] = list()
        metadata['height'] = list()
        metadata['width'] = list()
        for f in filenames:
            n_series = self.omexml_images[f].image_count
            # The number of series corresponds to the number of planes
            # within the image file.
            for s in xrange(n_series):
                image = self.omexml_images[f].image(s)
                # Create an instance of class ChannelImageMetadata for each channel
                # specified in an OMEXML *Image* element.
                # It is assumed that all *Plane* elements where
                # acquired at the same site, i.e. microscope stage position.
                pixels = image.Pixels
                n_planes = pixels.plane_count
                if n_planes == 0:
                    # Sometimes an image doesn't have any plane elements.
                    # Let's create them for consistency.
                    pixels = self._create_channel_planes(pixels)
                    n_planes = pixels.plane_count  # update plane count

                bit_depth = get_bit_depth(image.Pixels.PixelType)
                metadata['bit_depth'].append(bit_depth)
                # Each metadata element represents an image, which could
                # correspond to an individual plane or a z-stack, i.e. a
                # collection of several focal planes for the same channel
                # and time point.
                for p in xrange(n_planes):
                    plane = pixels.Plane(p)
                    metadata['name'].append(image.Name)
                    metadata['channel_name'].append(pixels.Channel(plane.TheC).Name)

                    metadata['tpoint'].append(plane.TheT)
                    metadata['zplane'].append(plane.TheZ)
                    # "TheC" will be defined later on, because this information
                    # is often not yet available at this point.
                    metadata['height'].append(pixels.SizeY)
                    metadata['width'].append(pixels.SizeX)

                    metadata['stage_position_y'].append(plane.PositionY)
                    metadata['stage_position_x'].append(plane.PositionX)

                    fm = ImageFileMapping()
                    fm.name = image.Name
                    fm.ref_index = i
                    fm.files = [f]
                    fm.series = [s]
                    fm.planes = [p]
                    self._file_mapper_list.append(fm)
                    self._file_mapper_lookup[image.Name].append(fm)

                    i += 1

        self.metadata = pd.DataFrame(metadata)
        length = self.metadata.shape[0]
        self.metadata['date'] = np.empty((length, ), dtype=str)
        self.metadata['well_name'] = np.empty((length, ), dtype=str)
        self.metadata['well_position_y'] = np.empty((length, ), dtype=int)
        self.metadata['well_position_x'] = np.empty((length, ), dtype=int)
        self.metadata['site'] = np.empty((length, ), dtype=int)

        return self.metadata

    def configure_omexml_from_metadata_files(self, regex):
        '''Uses the *OMEXML* metadata retrieved form additional
        microscope metadata files to complement metadata retrieved
        from microscope image files.

        Additional metadata files contain information that is not available
        from individual image files, for example information about wells.

        Parameters
        ----------
        regex: str
            named regular expression

        Returns
        -------
        pandas.DataFrame
            metadata for each 2D *Plane* element

        Note
        ----
        The OME schema doesn't provide information about wells at the individual
        *Image* level: see `OME data model <http://www.openmicroscopy.org/Schemas/Documentation/Generated/OME-2015-01/ome.html>`_.
        Instead, it provides a *Plate* element, which contains *Well* elements.
        *Well* elements contain the positional information, such as row and
        column index of each well within the plate. The *WellSample* elements
        represent individual image acquisition sites within a well and can hold
        metadata, such as the x and y positions of the *WellSample* within the
        *Well*. In addition, there is an *ImageRef* element, which can be used
        to map a *WellSample* to the corresponding *Image* elements.

        Custom handlers must provide the metadata from additional files
        as a single *OMEXML* object that holds the information for all images.
        This is in contrast to the way metadata is handled for individual
        images, where there is a separate *OMEXML* object for each image file.
        The value of the *image_count* attribute must equal
        *number of channels* x *number of focal planes* x
        *number of time series* x *number of acquisition sites*.
        The *Name* attribute of each *Image* element can be set with the
        image filename, in which the corresponding *Plane* element is stored.
        This information can serve as a reference to match additionally
        provided information. The values of the *SizeT*,
        *SizeC* and *SizeZ* attributes still have to match the actual pattern
        in the image files, however. For example, if the image file contains
        planes for one time point, one acquisition site
        and 10 focal planes, then *SizeT* == 1, *SizeC* == 1 and *SizeZ*
        == 10. Thereby we can keep track of individual planes upon formatting.

        Custom handlers are further required to provide information for the
        SPW *Plate* element. For consistency a slide should be represented
        as a plate with a single *Well* element.
        The *ImageRef* attribute of *WellSample* elements must be provided in
        form of a dictionary with keys *w*, *s*, *t*, *c*, *z* for
        "well", "site", "time", "channel" and "z dimension" information,
        respectively.

        Warning
        -------
        If the *Name* attribute of *Image* elements is not set,
        `python-bioformats` automatically assigns the name "default.png".
        *Image* elements with this name are assumed to be irrelevant
        and consequently skipped, i.e. the corresponding metadata entries are
        not updated.

        Raises
        ------
        NotSupportedError
            when metadata specifies more than one *Plate* element
            or when *Plane* elements have different x, y positions
        MetadataError
            when no additional metadata is available or when *Plate* element
            provides no or incorrect references to image files
        '''
        if self.omexml_metadata.image_count == 0:
            logger.info('no additional metadata provided')
            return self.metadata

        if not regex:
            regex = self.IMAGE_FILE_REGEX_PATTERN
        if not regex:
            raise RegexError('No regular expression provided.')

        logger.info('configure OMEXML provided by additional files')

        # NOTE: The value of the "image_count" attribute must equal the
        # total number of planes.
        n_images = self.omexml_metadata.image_count
        if not n_images == self.metadata.shape[0]:
            logger.warning(
                'number of images specified in metadata doesn\'t match the '
                'number of available images'
            )
            # raise MetadataError('Incorrect number of images.')

        md = self.metadata

        lookup = dict()
        r = re.compile(regex)
        matches = {
            tuple(r.search(name).groupdict().values()): name
            for name in md.name
        }
        for i in xrange(n_images):

            # Only consider image elements for which the value of the *Name*
            # attribute matches.
            image = self.omexml_metadata.image(i)
            pixels = image.Pixels
            name = image.Name
            try:
                matched_name = matches[tuple(r.search(name).groupdict().values())]
            except KeyError:
                logger.warning('image #%d "%s" is missing', i, name)
                continue
            idx = md[md.name == matched_name].index[0]
            # Individual image elements need to be mapped to well sample
            # elements in the well plate. The custom handlers provide a
            # regular expression, which is supposed to match a pattern in the
            # image filename and is able to extract the required information.
            # Here we create a lookup table with a mapping of captured matches
            # to the index of the corresponding image element.
            if len(self._file_mapper_list[idx].files) > 1:
                raise MetadataError('There should only be a single filename.')
            filename = os.path.basename(self._file_mapper_list[idx].files[0])
            match = r.search(filename)
            if not match:
                raise RegexError(
                    'Incorrect reference to image files in plate element.'
                )
            captures = match.groupdict()
            if 'z' not in captures.keys():
                captures['z'] = md.at[idx, 'zplane']
            else:
                # NOTE: quick and dirty hack for CellVoyager microscope,
                # which doesn't write the z index into the image file
                md.at[idx, 'zplane'] = captures['z']
            index = sorted(captures.keys())
            key = tuple([captures[ix] for ix in index])
            lookup[key] = idx

            if pixels.channel_count > 1:
                raise NotSupportedError(
                    'Only image elements with one channel are supported.'
                )

            if hasattr(image, 'AcquisitionDate'):
                md.at[idx, 'date'] = image.AcquisitionDate

            if hasattr(pixels.Channel(0), 'Name'):
                md.at[idx, 'channel_name'] = pixels.Channel(0).Name

            if (hasattr(pixels.Plane(0), 'PositionX') and
                    hasattr(pixels.Plane(0), 'PositionY')):
                md.at[idx, 'stage_position_x'] = pixels.Plane(0).PositionX
                md.at[idx, 'stage_position_y'] = pixels.Plane(0).PositionY


        # NOTE: Plate information is usually not readily available from images
        # or additional metadata files and thus requires custom readers/handlers
        plate = self.omexml_metadata.plates[0]
        for w in plate.Well:
            well = plate.Well[w]
            n_samples = len(well.Sample)
            for i in xrange(n_samples):
                # Find the reference *Image* elements for the current
                # well sample using the above created lookup table
                reference = well.Sample[i].ImageRef
                index = sorted(reference.keys())
                key = tuple([reference[ix] for ix in index])
                image_id = lookup[key]
                md.at[image_id, 'well_name'] = w

        return self.metadata

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
        if any(md['channel_name'].isnull()):
            missing_metadata.add('channel')
        if any(md['zplane'].isnull()):
            missing_metadata.add('focal plane')
        if any(md['tpoint'].isnull()):
            missing_metadata.add('time point')
        return missing_metadata

    def configure_metadata_from_filenames(self, plate_dimensions, regex):
        '''Configures metadata based on information encoded in image filenames
        using a regular expression with named groups:
            - *w*: well
            - *t*: time point
            - *s*: acquisition site
            - *z*: focal plane (z dimension)
            - *c*: channel

        For details on how to build a named regular expression
        please refer to documentation of the `re` package for
        `regular expression syntax <https://docs.python.org/2/library/re.html#regular-expression-syntax>`_.

        Expressions can be tested conveniently online at
        `pythex.org <http://pythex.org/>`_. Here is an
        `example <http://pythex.org/?regex=%5B%5E_%5D%2B_(%3FP%3Cw%3E%5Cw%2B)_T(%3FP%3Ct%3E%5Cd%2B)F(%3FP%3Cs%3E%5Cd%2B)L%5Cd%2BA%5Cd%2BZ(%3FP%3Cz%3E%5Cd%2B)C(%3FP%3Cc%3E%5Cd%2B)%5C.&test_string=150820-Testset-CV-2_D03_T0001F001L01A01Z01C02.tif&ignorecase=0&multiline=0&dotall=0&verbose=0>`_
        of a named regular expression string for retrieval of information from
        an image filename generated by the Yokogawa CellVoyager microscope.

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
        md = self.metadata
        filenames = natsorted(list(set([
            f for fm in self._file_mapper_list for f in fm.files
        ])))
        if md.shape[0] != len(filenames):
            raise MetadataError(
                'Configuration of metadata based on filenames '
                'works only when each image file contains a single plane.'
            )

        if not regex:
            regex = self.IMAGE_FILE_REGEX_PATTERN
        if not regex:
            raise RegexError('No regular expression provided.')

        provided_fields = re.findall(r'\(\?P\<(\w+)\>', regex)
        possible_fields = {'w', 'c', 'z', 's', 't'}
        required_fields = {'c', 's'}
        defaults = {'w': 'A01', 'z': 0, 't': 0}
        for name in provided_fields:
            if name not in possible_fields:
                raise RegexError(
                    '"%s" is not a supported regular expression field.\n'
                    'Supported are "%s"'
                    % (name, '", "'.join(required_fields))
                )
            if name not in required_fields:
                logger.warning(
                    'regular expression field "%s" not provided, defaults to %s',
                    (name, str(defaults[name]))
                )

        for name in required_fields:
            if name not in provided_fields:
                raise RegexError(
                    'Regular expression must contain field "%s"', name
                )

        logger.info('retrieve metadata from filenames via regular expression')
        logger.debug('expression: %s', regex)

        logger.info('update image metadata with filename information')

        r = re.compile(regex)
        for i, f in enumerate(filenames):
            match = r.search(f)
            if not match:
                raise RegexError(
                    'Metadata could not be retrieved from filename "%s" '
                    'using regular expression "%s"' % (f, regex)
                )
            # Not every microscope provides all the information in the filename.
            capture = match.groupdict()
            md.at[i, 'channel_name'] = str(capture['c'])
            md.at[i, 'site'] = int(capture['s'])
            md.at[i, 'zplane'] = int(capture.get('z', defaults['z']))
            md.at[i, 'tpoint'] = int(capture.get('t', defaults['t']))
            md.at[i, 'well_name'] = str(capture.get('w', defaults['w']))

        return self.metadata

    @staticmethod
    def _calculate_coordinates(positions):
        coordinates = stitch.calc_grid_coordinates_from_positions(positions)
        return coordinates

    def determine_grid_coordinates_from_stage_positions(self):
        '''Determines the coordinates of each image acquisition site within the
        overall continuous acquisition grid (slide or well in a plate)
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
        :py:func:`illuminati.stitch.calc_grid_coordinates_from_positions`
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

        for well_name in np.unique(md.well_name):

            ix = np.where(md.well_name == well_name)[0]
            positions = zip(
                md.loc[ix, 'stage_position_y'], md.loc[ix, 'stage_position_x']
            )

            coordinates = self._calculate_coordinates(positions)

            md.loc[ix, 'well_position_y'] = [site[0] for site in coordinates]
            md.loc[ix, 'well_position_x'] = [site[1] for site in coordinates]

        return self.metadata

    def determine_grid_coordinates_from_layout(self,
                                               stitch_layout,
                                               stitch_major_axis,
                                               stitch_dimensions=None):
        '''Determines the coordinates of each image acquisition site within the
        overall continuous acquisition grid (slide or well in a plate)
        based on a provided layout.

        Parameters
        ----------
        stitch_layout: str
            layout of the acquisition grid
            (``"horizontal"``, ``"zigzag_horizontal"``, ``"vertical"``,
             or ``"zigzag_vertical"``)
        stitch_major_axis: str
            longer axis of the acquisition grid
            (``"vertical"`` or ``"horizontal"``)
        stitch_dimensions: Tuple[int], optional
            dimensions of the acquisition grid, i.e. number of images
            along each axis

        Returns
        -------
        pandas.DataFrame
            metadata for each 2D *Plane* element

        See also
        --------
        :py:func:`illuminati.stitch.guess_stitch_dimensions`
        :py:func:`illuminati.stitch.calc_grid_coordinates_from_layout`
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

        if not any(stitch_dimensions):
            stitch_dimensions = stitch.guess_stitch_dimensions(
                                    n_sites, stitch_major_axis)

        logger.debug('stitch layout: {0}; stitch dimensions: {1}'.format(
                     stitch_layout, stitch_dimensions))

        coordinates = stitch.calc_grid_coordinates_from_layout(
                                    stitch_dimensions, stitch_layout)

        sites = acquisitions_per_well.groups.values()

        for indices in sites:
            # TODO: make sure metadata is sorted according to
            # acquisition site
            y_coordinates = [c[0] for c in coordinates]
            x_coordinates = [c[1] for c in coordinates]
            md.loc[indices, 'well_position_y'] = y_coordinates
            md.loc[indices, 'well_position_x'] = x_coordinates

        return self.metadata

    def group_metadata_per_zstack(self):
        '''All focal planes belonging to one z-stack (i.e. that were acquired
        at different z resolutions but at the same microscope stage position,
        time point and channel) are grouped together.

        Returns
        -------
        pandas.DataFrame
            metadata for each 2D *Plane* element
        '''
        md = self.metadata

        logger.info('group metadata per z-stack')

        # Remove all z-plane image entries except for the first
        grouped_md = md.drop_duplicates(subset=[
            'well_name', 'well_position_x', 'well_position_y',
            'channel_name', 'tpoint'
        ]).copy()
        grouped_md.index = range(grouped_md.shape[0])
        # NOTE: z-planes will no only be tracked via the file mapping

        # Group metadata by focal planes (z-stacks)
        zstacks = md.groupby([
            'well_name', 'well_position_x', 'well_position_y',
            'channel_name', 'tpoint'
        ])
        logger.debug('identified %d z-stacks', zstacks.ngroups)

        # Map the locations of each plane with the original image files
        # in order to be able to perform the intensity projection later on
        grouped_file_mapper_list = list()
        for i, indices in enumerate(sorted(zstacks.groups.values())):
            fm = ImageFileMapping()
            fm.files = list()
            fm.series = list()
            fm.planes = list()
            fm.zlevels = list()
            for index in indices:
                fm.ref_index = i  # new index
                fm.files.extend(self._file_mapper_list[index].files)
                fm.series.extend(self._file_mapper_list[index].series)
                fm.planes.extend(self._file_mapper_list[index].planes)
                fm.zlevels.append(md.loc[index, 'zplane'])
            grouped_file_mapper_list.append(fm)

        # Update metadata and file mapper objects
        self.metadata = grouped_md
        self._file_mapper_list = grouped_file_mapper_list

        return self.metadata

    def update_channel(self):
        '''Creates for each channel a zero-based unique identifier number.

        Returns
        -------
        pandas.DataFrame
            metadata for each 2D *Plane* element

        Note
        ----
        The id may not reflect the order in which the channels were acquired
        on the microscope.

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

        return self.metadata

    def update_zplane(self):
        '''Creates for each focal plane a zero-based unique identifier number.

        Returns
        -------
        pandas.DataFrame
            metadata for each 2D *Plane* element

        Note
        ----
        The id may not reflect the order in which the planes were acquired
        on the microscope.

        Warning
        -------
        Apply this method only at the end of the configuration process.
        '''
        logger.info('update z-plane index')
        md = self.metadata
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
        site_indices = sorted(sites.groups.values())
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

    def create_image_file_mapping(self):
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
        logger.info('build image file mapping')
        md = self.metadata
        mapper = dict()
        for item in self._file_mapper_list:
            mapper[item.ref_index] = item.as_dict()
        return mapper


class MetadataReader(object):

    '''Abstract base class for reading metadata from additional (non-image) files.

    They return metadata as OMEXML objects, according to the OME data model,
    see `python-bioformats <http://pythonhosted.org/python-bioformats/#metadata>`_.

    Unfortunately, the documentation is very sparse.
    If you need additional information, refer to the relevant
    `source code <https://github.com/CellProfiler/python-bioformats/blob/master/bioformats/omexml.py>`_.

    Note
    ----
    In case custom readers provide a *Plate* element, they also have to specify
    an *ImageRef* elements for each *WellSample* element, which serve as
    references to OME *Image* elements. Each *ImageRef* attribute must be a
    dictionary with a single entry. The value must be a list of strings, where
    each element represents the reference information that can be used to map
    the *WellSample* element to an individual *Image* element. The key must be
    a regular expression string that can be used to extract the reference
    information from the corresponding image filenames.
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
        '''Reads metadata from vendor specific files on disk.

        Parameters
        ----------
        microscope_metadata_files: List[str]
            absolute path to the microscope metadata files
        microscope_image_files: List[str]
            absolute path to the microscope image files

        Returns
        -------
        str
            OMEXML metadata
        '''
        pass
