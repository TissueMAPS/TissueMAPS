import os
import re
import bioformats
import logging
import numpy as np
import pandas as pd
from natsort import natsorted
from collections import defaultdict
from cached_property import cached_property
from abc import ABCMeta
from abc import abstractproperty
from .ome_xml import XML_DECLARATION
from ..metadata import ImageFileMapper
from ..illuminati import stitch
from .. import utils
from ..errors import MetadataError
from ..errors import RegexError
from ..errors import NotSupportedError
from ..readers import MetadataReader

logger = logging.getLogger(__name__)


class MetadataHandler(object):

    '''
    Abstract base class for handling image data and associated metadata from
    heterogeneous microscope file formats as provided by the
    `Bio-Formats <http://www.openmicroscopy.org/site/products/bio-formats>`_
    library.

    Original metadata has to be available as OME-XML according to the
    `OME schema <http://www.openmicroscopy.org/Schemas/Documentation/Generated/OME-2015-01/ome.html>`_.

    The metadata that can be automatically retrieved form image files may not
    be sufficient, but may require additional microscope-specific metadata
    and/or user input.
    '''

    __metaclass__ = ABCMeta

    def __init__(self, image_files, additional_files, omexml_files, plate_name):
        '''
        Initialize an instance of class MetadataHandler.

        Parameters
        ----------
        image_files: List[str]
            full paths to image files
        additional_files: List[str]
            full paths to additional microscope-specific metadata files
        omexml_files: List[str]
            full paths to the XML files that contain the extracted OMEXML data
        plate_name: str
            name of the corresponding plate
        '''
        self.image_files = image_files
        self.additional_files = additional_files
        self.omexml_files = omexml_files
        self.plate_name = plate_name
        self.metadata = pd.DataFrame(
            columns=[
                'name', 'date',
                'tpoint_ix', 'zplane_ix', 'channel_ix', 'channel_name',
                'well_id', 'well_position_y', 'well_position_x', 'site_ix',
                'stage_position_y', 'stage_position_x'
            ]
        )
        self.file_mapper_list = list()
        self.file_mapper_lookup = defaultdict(list)
        self.id_to_well_id_ref = dict()
        self.id_to_wellsample_ix_ref = dict()
        self.wells = dict()

    @cached_property
    def ome_image_metadata(self):
        '''
        Read the OMEXML metadata extracted from image files.

        Returns
        -------
        Dict[str, bioformats.omexml.OMEXML]
            metadata for each original image file

        See also
        --------
        :py:class:`tmlib.metareaders.DefaultMetadataReader`
        '''
        self._ome_image_metadata = dict()
        logger.info('read OMEXML metadata extracted from image files')
        with DefaultMetadataReader() as reader:
            for i, f in enumerate(self.omexml_files):
                k = os.path.basename(self.image_files[i])
                self._ome_image_metadata[k] = reader.read(f)
        return self._ome_image_metadata

    @staticmethod
    def _create_channel_planes(pixels):
        '''
        Add new `Plane` elements to an existing OMEXML `Pixels` element for
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

        sorted_attributes = sorted([(channel_position, 'TheC'),
                                    (stack_position, 'TheZ'),
                                    (time_position, 'TheT')])

        sorted_counts = sorted([(channel_position, n_channels),
                                (stack_position, n_stacks),
                                (time_position, n_stacks)])

        count = 0
        for i in xrange(sorted_counts[0][1]):
            for j in xrange(sorted_counts[1][1]):
                for k in xrange(sorted_counts[2][1]):
                    setattr(pixels.Plane(count), sorted_attributes[0][1], i)
                    setattr(pixels.Plane(count), sorted_attributes[1][1], j)
                    setattr(pixels.Plane(count), sorted_attributes[2][1], k)
                    count += 1

        return pixels

    def configure_ome_metadata_from_image_files(self):
        '''
        Collect image metadata from individual `OMEXML` elements (one for each
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
        filenames = natsorted(self.ome_image_metadata.keys())
        for f in filenames:
            n_series = self.ome_image_metadata[f].image_count
            # The number of series corresponds to the number of planes
            # within the image file.
            for s in xrange(n_series):
                image = self.ome_image_metadata[f].image(s)
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

                # Each metadata element represents an image, which could
                # correspond to an individual plane or a z-stack, i.e. a
                # collection of several focal planes for the same channel
                # and time point.
                for p in xrange(n_planes):
                    plane = pixels.Plane(p)
                    md = self.metadata
                    md.at[i, 'name'] = image.Name
                    md.at[i, 'channel_name'] = pixels.Channel(plane.TheC).Name

                    md.at[i, 'tpoint_ix'] = plane.TheT
                    md.at[i, 'zplane_ix'] = plane.TheZ
                    # "TheC" will be defined later on, because this information
                    # is often not yet available at this point.

                    md.at[i, 'stage_position_x'] = plane.PositionX
                    md.at[i, 'stage_position_y'] = plane.PositionY

                    fm = ImageFileMapper()
                    fm.name = md.name
                    fm.ref_index = i
                    fm.files = [f]
                    fm.series = [s]
                    fm.planes = [p]
                    self.file_mapper_list.append(fm)
                    self.file_mapper_lookup[md.at[i, 'name']].append(fm)

                    i += 1

            # NOTE: Columns must have numpy data types, otherwise the
            # serialization via PyTables will fail
            md.tpoint_ix = md.tpoint_ix.astype(int)
            md.zplane_ix = md.zplane_ix.astype(int)
            md.stage_position_y = md.stage_position_y.astype(float)
            md.stage_position_x = md.stage_position_x.astype(float)

        return self.metadata

    @abstractproperty
    def ome_additional_metadata(self):
        '''
        Returns
        -------
        bioformats.omexml.OMEXML
            metadata retrieved from additional microscope specific files
            with an image element for each ultimately extracted image
        '''
        pass

    def configure_ome_metadata_from_additional_files(self):
        '''
        Use the *OMEXML* metadata retrieved form additional microscope-specific
        metadata files to complement metadata retrieved from image files.

        Additional metadata files contain information that is not available
        from individual image files, for example information about wells.

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

        See also
        --------
        :py:class:`tmlib.metaconfig.default.MetaDataHandler`
        :py:class:`tmlib.metaconfig.visiview.VisiviewMetaDataHandler`
        :py:class:`tmlib.metaconfig.cellvoyager.CellvoyagerMetaDataHandler`
        '''
        if self.ome_additional_metadata.image_count == 0:
            # One image is always added by default.
            logger.info('no additional metadata provided')

            return self.metadata

        if not self.REGEX:
            raise RegexError('No regular expression available.')

        logger.info('configure OMEXML provided by additional files')

        # NOTE: The value of the "image_count" attribute must equal the
        # total number of planes.
        n_images = self.ome_additional_metadata.image_count
        if not n_images == self.metadata.shape[0]:
            raise MetadataError('Incorrect number of images.')

        md = self.metadata

        lookup = dict()
        r = re.compile(self.REGEX)
        for i in xrange(n_images):
            # Individual image elements need to be mapped to well sample
            # elements in the well plate. The custom handlers provide a
            # regular expression, which is supposed to match a pattern in the
            # image filename and is able to extract the required information.
            # Here we create a lookup table with a mapping of captured matches
            # to the index of the corresponding image element.
            if len(self.file_mapper_list[i].files) > 1:
                raise ValueError('There should only be a single filename.')
            filename = os.path.basename(self.file_mapper_list[i].files[0])
            match = r.search(filename)
            if not match:
                raise RegexError(
                        'Incorrect reference to image files in plate element.')
            captures = match.groupdict()
            if 'z' not in captures.keys():
                captures['z'] = md.at[i, 'zplane_ix']
            index = sorted(captures.keys())
            key = tuple([captures[ix] for ix in index])
            lookup[key] = i

            # Only consider image elements for which the value of the *Name*
            # attribute matches.
            image = self.ome_additional_metadata.image(i)
            pixels = image.Pixels
            name = image.Name
            matched_indices = md[md.name == name].index

            if pixels.channel_count > 1:
                raise NotSupportedError(
                        'Only image elements with one channel are supported.')

            for ix in matched_indices:

                if hasattr(image, 'AcquisitionDate'):
                    md.at[ix, 'date'] = image.AcquisitionDate

                if hasattr(pixels.Channel(0), 'Name'):
                    md.at[ix, 'channel_name'] = pixels.Channel(0).Name

                if (hasattr(pixels.Plane(0), 'PositionX') and
                        hasattr(pixels.Plane(0), 'PositionY')):
                    md.at[ix, 'stage_position_x'] = pixels.Plane(0).PositionX
                    md.at[ix, 'stage_position_y'] = pixels.Plane(0).PositionY


        # NOTE: Plate information is usually not readily available from images
        # or additional metadata files and thus requires custom readers/handlers
        plate = self.ome_additional_metadata.plates[0]
        for well_id in plate.Well:
            well = plate.Well[well_id]
            n_samples = len(well.Sample)
            for i in xrange(n_samples):
                # Find the reference *Image* elements for the current
                # well sample using the above created lookup table
                reference = well.Sample[i].ImageRef
                index = sorted(reference.keys())
                key = tuple([reference[ix] for ix in index])
                image_id = lookup[key]
                md.at[image_id, 'well_id'] = well_id

        return self.metadata

    def determine_missing_metadata(self):
        '''
        Determine if required basic metadata information, such as
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
        if any(md['zplane_ix'].isnull()):
            missing_metadata.add('focal plane')
        if any(md['tpoint_ix'].isnull()):
            missing_metadata.add('time point')
        return missing_metadata

    def configure_metadata_from_filenames(self, plate_dimensions, regex=None):
        '''
        Configure metadata based on information encoded in image filenames
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
            f for fm in self.file_mapper_list for f in fm.files
        ])))
        if md.shape[0] != len(filenames):
            raise MetadataError(
                    'Configuration of metadata based on filenames '
                    'works only when each image file contains a single plane.')

        if not regex:
            regex = self.REGEX
        if not regex:
            raise RegexError('No regular expression provided.')

        provided_names = re.findall(r'\(\?P\<(\w+)\>', regex)
        required_names = {'w', 'c', 'z', 's', 't'}
        for name in provided_names:
            if name not in required_names:
                raise RegexError(
                        '"%s" is not a supported group name.\n'
                        'Supported are "%s"'
                        % (name, '", "'.join(required_names)))

        for name in required_names:
            if name not in provided_names:
                raise RegexError(
                        'Expression must contain group name "%s"', name)

        logger.info('retrieve metadata from filenames via regular expression')
        logger.debug('expression: %s', regex)

        logger.info('update image metadata')

        r = re.compile(regex)
        for i, f in enumerate(filenames):
            match = r.search(f)
            if not match:
                raise RegexError(
                        'Metadata could not be retrieved from filename "%s" '
                        'using regular expression "%s"' % (f, regex))
            capture = match.groupdict()
            md.at[i, 'channel_name'] = capture['c']
            md.at[i, 'zplane_ix'] = capture['z']
            md.at[i, 'tpoint_ix'] = capture['t']
            md.at[i, 'well_id'] = capture['w']
            md.at[i, 'site_ix'] = capture['s']

        return self.metadata

    @staticmethod
    def _calculate_coordinates(positions):
        coordinates = stitch.calc_grid_coordinates_from_positions(positions)
        return coordinates

    def determine_grid_coordinates_from_stage_positions(self):
        '''
        Determine the coordinates of each image acquisition site within the
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
                    'Stage position information is not available.')

        logger.info('translate absolute microscope stage positions into '
                    'relative acquisition grid coordinates')

        for well_id in np.unique(md.well_id):

            ix = np.where(md.well_id == well_id)[0]
            positions = zip(md.loc[ix, 'stage_position_y'],
                            md.loc[ix, 'stage_position_x'])

            coordinates = self._calculate_coordinates(positions)

            md.loc[ix, 'well_position_y'] = [site[0] for site in coordinates]
            md.loc[ix, 'well_position_x'] = [site[1] for site in coordinates]

        return self.metadata

    def determine_grid_coordinates_from_layout(self,
                                               stitch_layout,
                                               stitch_major_axis,
                                               stitch_dimensions=None):
        '''
        Determine the coordinates of each image acquisition site within the
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
            'well_id', 'channel_name', 'zplane_ix', 'tpoint_ix'
        ])

        n_acquisitions_per_well = acquisitions_per_well.count().name

        if len(np.unique(n_acquisitions_per_well)) > 1:
            raise MetadataError(
                    'Each well must have the same number of acquisition sites.')

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

    def reconfigure_ome_metadata_for_projection(self):
        '''
        Reconfigure metadata in order to account for subsequent intensity
        projection.
        To this end, each z-stack (all focal planes acquired at
        at different z resolutions but at the same microscope stage position,
        at the "same" time point and in the same channel) is reduced to a
        single 2D plane.

        Returns
        -------
        pandas.DataFrame
            metadata for each 2D *Plane* element
        '''
        md = self.metadata

        logger.info('reconfigure metadata for intensity projection')

        # Remove all z-plane image entries except for the first
        projected_md = md.drop_duplicates([
            'well_id', 'well_position_x', 'well_position_y',
            'channel_name', 'tpoint_ix'
        ]).reindex()
        # Update z-plane index for the projected image entries
        projected_md.zplane_ix = 0
        # Names may no longer be accurate and will be updated separately
        projected_md.name = None

        # Group metadata by focal planes (z-stacks)
        zstacks = md.groupby([
            'well_id', 'well_position_x', 'well_position_y',
            'channel_name', 'tpoint_ix'
        ])
        logger.debug('identified %d z-stacks', zstacks.ngroups)

        # Map the locations of each plane with the original image files
        # in order to be able to perform the intensity projection later on
        projected_file_mapper_list = list()
        for i, indices in enumerate(zstacks.groups.values()):
            fm = ImageFileMapper()
            fm.ref_index = i
            fm.files = list()
            fm.series = list()
            fm.planes = list()
            for ref_ix in indices:
                fm.files.extend(self.file_mapper_list[ref_ix].files)
                fm.series.extend(self.file_mapper_list[ref_ix].series)
                fm.planes.extend(self.file_mapper_list[ref_ix].planes)
            projected_file_mapper_list.append(fm)

        # Replace metadata and file mapper objects
        self.metadata = projected_md
        self.file_mapper_list = projected_file_mapper_list

        return self.metadata

    def update_channel_ixs(self):
        '''
        Create for each channel a zero-based unique identifier number.

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
        logger.info('update channel ids')
        md = self.metadata
        channels = np.unique(md.channel_name)
        for i, c in enumerate(channels):
            md.loc[(md.channel_name == c), 'channel_ix'] = i

        md.channel_ix = md.channel_ix.astype(int)

        return self.metadata

    def update_zplane_ixs(self):
        '''
        Create for each focal plane a zero-based unique identifier number.

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
        logger.info('update plane ids')
        md = self.metadata
        zplanes = np.unique(md.zplane_ix)
        for i, z in enumerate(zplanes):
            md.loc[(md.zplane_ix == z), 'zplane_ix'] = i
        return self.metadata

    def build_image_filenames(self, image_file_format_string):
        '''
        Build unique filenames for extracted images.

        Since the number of extracted images may be different than the number
        of image source files (because each image file can contain multiple
        planes), new names have to be build for the target files.

        Parameters
        ----------
        image_file_format_string: str
            Python format string with the following fieldnames: "plate_name",
            "w", x", "y", "c", "z", "t"

        Returns
        -------
        pandas.DataFrame
            metadata for each 2D *Plane* element
        '''
        logger.info('build names for final image files')
        md = self.metadata
        for i in xrange(md.shape[0]):
            fieldnames = {
                'plate_name': self.plate_name,
                'w': md.at[i, 'well_id'],
                'y': md.at[i, 'well_position_y'],
                'x': md.at[i, 'well_position_x'],
                'c': md.at[i, 'channel_ix'],
                'z': md.at[i, 'zplane_ix'],
                't': md.at[i, 'tpoint_ix'],
            }
            md.at[i, 'name'] = image_file_format_string.format(**fieldnames)

        return self.metadata

    def assign_acquisition_site_indices(self):
        '''
        Give each acquisition site a globally (plate-wide) unique index.

        Returns
        -------
        pandas.DataFrame
            metadata for each 2D *Plane* element
        '''
        logger.info('assign plate wide acquisition site indices')
        md = self.metadata
        sites = md.groupby([
            'well_id', 'well_position_x', 'well_position_y'
        ])
        site_indices = sorted(sites.groups.values())
        for i, indices in enumerate(site_indices):
            md.loc[indices, 'site_ix'] = i

        md.site_ix = md.site_ix.astype(int)

        return self.metadata

    def remove_redundant_columns(self):
        '''
        Clean-up metadata, i.e. remove information that is no longer required.

        Returns
        -------
        pandas.DataFrame
            metadata for each 2D *Plane* element
        '''
        logger.info('remove redundant metadata')
        logger.debug('remove column "stage_position_y"')
        del self.metadata.stage_position_y
        logger.debug('remove column "stage_position_x"')
        del self.metadata.stage_position_x

        return self.metadata

    def create_image_file_mapper(self):
        '''
        Create a hashmap for the extraction of individual planes from the
        original image files.

        Returns
        -------
        Dict[str, Dict[str, List[str]]]
            key-value pairs to map the original image filename to the
            *name* of each extracted image and the *series* and *plane*,
            which specify the location in the original file, from where the
            image plane should be extracted
        '''
        logger.info('build image file mapper')
        md = self.metadata
        mapper = list()
        if len(self.file_mapper_list[0].files) > 1:
            # In this case individual focal planes that should be projected
            # to the final 2D plane are distributed across several files.
            # These files have to be loaded on the same node in order to be
            # able to perform the projection.
            for i in xrange(md.shape[0]):
                element = ImageFileMapper()
                element.ref_index = i
                element.ref_file = md.at[i, 'name']
                element.files = self.file_mapper_list[i].files
                element.series = self.file_mapper_list[i].series
                element.planes = self.file_mapper_list[i].planes
                mapper.append(dict(element))
        else:
            # In this case images files contain one or multiple planes
            filenames = [f for fm in self.file_mapper_list for f in fm.files]
            for f in filenames:
                ix = utils.indices(filenames, f)
                for i in ix:
                    element = ImageFileMapper()
                    element.ref_index = i
                    element.ref_file = md.at[i, 'name']
                    element.files = [f]
                    element.series = self.file_mapper_list[i].series
                    element.planes = self.file_mapper_list[i].planes
                    mapper.append(dict(element))

        return mapper


class DefaultMetadataHandler(MetadataHandler):

    '''
    Class for handling image metadata in standard cases where additional
    metadata files are not required or not available.
    '''

    REGEX = ''

    def __init__(self, image_files, additional_files, omexml_files, plate_name):
        '''
        Initialize an instance of class MetadataHandler.

        Parameters
        ----------
        image_files: List[str]
            full paths to image files
        additional_files: List[str]
            full paths to additional microscope-specific metadata files
        omexml_files: List[str]
            full paths to the XML files that contain the extracted OMEXML data
        plate_name: str
            name of the corresponding plate

        Returns
        -------
        tmlib.metaconfig.default.DefaultMetadataHandler
        '''
        super(DefaultMetadataHandler, self).__init__(
                image_files, additional_files, omexml_files, plate_name)
        self.image_files = image_files
        self.additional_files = additional_files
        self.omexml_files = omexml_files
        self.plate_name = plate_name

    @property
    def ome_additional_metadata(self):
        '''
        Returns
        -------
        bioformats.omexml.OMEXML
            empty object
        '''
        self._ome_additional_metadata = bioformats.OMEXML(XML_DECLARATION)
        # Add an empty *Plate* element
        self._ome_additional_metadata.PlatesDucktype(
                    self._ome_additional_metadata.root_node).newPlate(
                    name='default')
        return self._ome_additional_metadata


class DefaultMetadataReader(MetadataReader):

    '''
    `Python-bioformats <https://github.com/CellProfiler/python-bioformats>`_
    provides an interface for reading metadata form image files
    using `python-javabridge <https://github.com/CellProfiler/python-javabridge>`_.

    However, this approach often leads to incorrect parsing of metadata due
    to problems related to the use of specific reader classes.
    Therefore, metadata is extracted from the image files directly via
    Bio-Formats using the
    `showinf <http://www.openmicroscopy.org/site/support/bio-formats5.1/users/comlinetools/display.html>`_
    command line tool. This tool prints the OME-XML to standard output, which
    is captured and redirected to a file.
    '''

    def read(self, filename):
        '''
        Read Open Microscopy Environment (OME) metadata from XML file on disk.

        Parameters
        ----------
        filename: str
            absolute path to the file

        Returns
        -------
        bioformats.omexml.OMEXML
            image metadata

        Raises
        ------
        tmlib.errors.NotSupportedError
            when the file format is not supported
        '''
        # ome_xml_data = bf.get_omexml_metadata(filename)
        with open(filename, 'r') as f:
            ome_xml_data = f.read()
        metadata = bioformats.OMEXML(ome_xml_data)
        return metadata
