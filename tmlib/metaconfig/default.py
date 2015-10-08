import os
import re
import bioformats
import logging
from collections import defaultdict
from cached_property import cached_property
from abc import ABCMeta
from abc import abstractproperty
from ..metadata import ChannelImageMetadata
from ..metadata import FileFormatMapper
from ..illuminati import stitch
from .. import utils
from ..errors import MetadataError
from ..errors import NotSupportedError
from ..errors import RegexpError
from ..experiment import WellPlate
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

    def __init__(self, image_files, additional_files, ome_xml_files,
                 experiment_name):
        '''
        Initialize an instance of class MetadataHandler.

        Parameters
        ----------
        image_upload_files: List[str]
            full paths to image files
        additional_files: List[str]
            full paths to additional microscope-specific metadata files
        ome_xml_files: List[str]
            full paths to the XML files that contain the extracted OMEXML data
        experiment_name: str
            name of the experiment
        '''
        self.image_files = image_files
        self.additional_files = additional_files
        self.ome_xml_files = ome_xml_files
        self.experiment_name = experiment_name
        self.file_mapper = list()

    @cached_property
    def ome_image_metadata(self):
        '''
        Read the OMEXML metadata extracted from image files.

        Returns
        -------
        Dict[str, bioformats.omexml.OMEXML]
            metadata retrieved from image files

        See also
        --------
        `tmlib.metareaders.DefaultMetadataReader`_
        '''
        self._ome_image_metadata = dict()
        logger.info('read OMEXML metadata')
        with DefaultMetadataReader() as reader:
            for i, f in enumerate(self.ome_xml_files):
                k = os.path.basename(self.image_files[i])
                self._ome_image_metadata[k] = reader.read(f)
        return self._ome_image_metadata

    @staticmethod
    def _create_channel_planes(pixels):
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

    def format_omexml_metadata(self, projection):
        '''
        Convert image metadata from `OMEXML` into custom format.

        Returns
        -------
        List[ChannelImageMetadata]
            formatted metadata objects
        projection: bool
            whether focal planes should be projected to a single 2D plane
            (dimensionality reduction)

        Note
        ----
        There must be one *OMEXML* object for each image file.
        An image file, however, may contain more than one *Image* element,
        which is referred to as a *Series*.
        Each *Image*/*Pixels* element contains at least one *Plane* element.
        A *Plane* represents a 2-dimensional pixel array for a given channel,
        z-section and time point. The different planes are often grouped
        together as a *Series* per acquisition site, i.e. microscope stage
        position (is this always the case?).
        Ultimately, we would like to create image files that contain only
        a single-channel plane image per file.
        To this end, the metadata hierarchy gets flattened, i.e. a separate
        *Image* element will be created for each *Plane* element.
        However, when `projection` is set to ``True`` several *Plane* elements
        will be grouped per *Image* element, but the resulting image will still
        be a 2D plane, due to the applied dimensionality reduction.

        See also
        --------
        `metadata.ChannelImageMetadata`_
        '''
        formatted_metadata = list()
        logger.info('convert OMEXML metadata to custom format')
        count = 0
        for i, f in enumerate(self.ome_image_metadata.keys()):
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
                    # Sometimes an image doesn't have plane elements.
                    # Let's create them for consistency.
                    pixels = self._create_channel_planes(pixels)
                    n_planes = pixels.plane_count  # update plane count

                if projection:
                    stacks = list()
                    # Group all focal planes in the image together to a z-stack
                    tpoints = [pixels.Plane(x).TheT for x in xrange(n_planes)]
                    channels = [pixels.Plane(x).TheC for x in xrange(n_planes)]
                    for t in tpoints:
                        for c in channels:
                            stacks.append([
                                pixels.Plane(x) for x in xrange(n_planes)
                                if pixels.Plane(x).TheT == t
                                and pixels.Plane(x).TheC == c
                            ])
                else:
                    stacks = [[pixels.Plane(x)] for x in xrange(n_planes)]

                # Each metadata element represents an image, which could
                # correspond to an individual plane or a z-stack, i.e. a
                # collection of several focal planes with the same channel
                # and time point.
                for p, stack in enumerate(stacks):
                    md = ChannelImageMetadata()
                    # This information should be identical across focal planes
                    plane = stack[0]
                    md.id = count
                    md.name = image.Name
                    md.channel_name = pixels.Channel(plane.TheC).Name
                    md.time_id = plane.TheT
                    md.stage_position = (plane.PositionY, plane.PositionX)
                    md.orig_dtype = pixels.PixelType
                    md.orig_dimensions = (pixels.SizeY, pixels.SizeX)
                    # Set focal plane identifier to zero in case of projection
                    if len(stack) > 1:
                        md.plane_id = 0
                        md.is_projected = True
                    else:
                        md.plane_id = plane.TheZ

                    ffm = FileFormatMapper()
                    ffm.name = md.name
                    ffm.filename = f
                    ffm.series = s
                    # Group planes in case of projection
                    if len(stack) > 1:
                        ffm.planes = range(len(stack))
                    else:
                        ffm.planes = [p]

                    formatted_metadata.append(md)
                    self.file_mapper.append(ffm)
                    count += 1

        return formatted_metadata

    @abstractproperty
    def ome_additional_metadata(self):
        '''
        Returns
        -------
        bioformats.omexml.OMEXML
            metadata retrieved from additional microscope specific files
        '''
        pass

    def _update_metadata(self, ome_image_element, metadata):
        # Update attribute values of ChannelImageMetadata objects.
        # We're not looping over all attributes, but only those that are known
        # to be missing for support microscope file formats and for which we
        # have custom readers for additional metadata files from where the
        # missing data can be retrieved
        updated_metadata = list(metadata)
        pixels = ome_image_element.Pixels

        n_planes = pixels.plane_count
        n_channels = pixels.SizeC
        if n_channels is not len(metadata):
            raise AssertionError('Number of channels must be identical.')
        for c in xrange(n_channels):
            md = updated_metadata[c]  # TODO
            # There must be a more elegant way...
            if not md.channel_name:
                try:
                    md.channel_name = pixels.Channel(c).Name
                except AttributeError:
                    pass
            if not any(md.stage_position):
                try:
                    planes = [
                        pixels.Plane(p) for p in xrange(n_planes)
                        if c == pixels.Plane(p).TheC
                    ]
                    md.stage_position = (planes[0].PositionY,
                                         planes[0].PositionX)
                except AttributeError:
                    pass
            updated_metadata[c] = md

        return updated_metadata

    def format_metadata_from_additional_files(self, metadata):
        '''
        Convert *OMEXML* metadata retrieved form additional microscope-specific
        metadata files into custom format and add it the metadata retrieved
        from image files.

        Additional metadata files contain information that is not available
        from individual image files, for example information about wells in
        case of a well plate format.

        Parameters
        ----------
        metadata: List[ChannelImageMetadata]
            image metadata

        Returns
        -------
        List[ChannelImageMetadata]
            complemented image metadata

        Note
        ----
        Since image-specific information is stored in *Image* elements and
        plate-specific information in a separate *Plate* element, one needs
        references from individual images to the corresponding wells.
        This can be achieved via *ImageRef* elements, which have to be set
        for each *WellSample* element in a plate. These references must be
        provided as substrings of the image filenames together with a matching
        regular expression string.

        There must be only one *OMEXML* object for all image files.
        This is in contrast to the metadata for individual images, where there
        is a separate *OMEXML* object for each image file. The
        microscope-specific readers are responsible to ensure that the *image
        count* matches.
        *image count* = *number of channels* x *number of focal planes*
        x *number of time series* x *number of sites*

        Warning
        -------
        *Image* elements with *Name* "default.png" are automatically created by
        `python-bioformats` when *image_count* is set. They are assumed to be
        empty and are ignored.

        Raises
        ------
        NotSupportedError
            when metadata specifies more than one *Plate* element
            or when *Plane* elements have different x, y positions
        MetadataError
            when *Plate* element provide no or incorrect references to
            image files or when no additional metadata is available

        See also
        --------
        `tmlib.metadata.ChannelImageMetadata`_
        '''
        if self.ome_additional_metadata is None:
            raise MetadataError('No additional metadata available')

        complemented_metadata = list(metadata)
        n_images = self.ome_additional_metadata.image_count
        # The number of images corresponds to the total number of
        # single-channel planes, i.e. the number of final image files that will
        # get extracted from the original image files and saved as PNG files.
        for i in xrange(n_images):
            if self.ome_additional_metadata.image(i).Name == 'default.png':
                # Setting the image count automatically creates empty image
                # elements with name "default.png". They can be skipped.
                continue
            image = self.ome_additional_metadata.image(i)
            # TODO: this might be not general enough, because it may happen
            # that the name of the image could not be determined or is not
            # provided by the microscope.
            matched_objects = {
                ix: metadata[ix]
                for ix, ffm in enumerate(self.file_mapper)
                if ffm.name == image.Name
            }
            updated_objects = self._update_metadata(
                                    image, matched_objects.values())
            for j, ix in enumerate(matched_objects.keys()):
                complemented_metadata[ix] = updated_objects[j]

        # Below is well plate specific stuff. This information can usually not
        # easily retrieved from images or metdata files without a custom reader
        plates = self.ome_additional_metadata.plates
        n_plates = len(plates)
        if n_plates == 0:
            for i in xrange(n_images):
                complemented_metadata[i].well_id = ''
                return complemented_metadata
        elif n_plates > 1:
            raise NotSupportedError('Only a single plate is supported.')
        n_wells = len(plates[0].Well)
        well_inf = dict()
        # User regular expression to find reference *Image* elements
        ref_regexp = re.compile(plates[0].Well[0].Sample[0].ImageRef.keys()[0])
        if not ref_regexp:
            raise MetadataError('No reference to image files.')
        for w in xrange(n_wells):
            well_row = plates[0].Well[w].Row
            well_col = plates[0].Well[w].Column
            well_pos = (well_row, well_col)
            well_samples = plates[0].Well[w].Sample
            ref_values = [well_samples[i].ImageRef.values()[0]
                          for i in xrange(len(well_samples))]
            if any(ref_values):
                ref_values = utils.flatten(ref_values)
            well_inf.update({n: well_pos for n in ref_values})

        if all(well_inf.keys()):
            for i, md in enumerate(complemented_metadata):
                ref_img = re.search(
                            ref_regexp,
                            os.path.basename(self.file_mapper[i].filename))
                if ref_img:
                    ref_img = ref_img.group(1)
                else:
                    raise MetadataError('Incorrect reference to image files.')
                ref_well = [well for ref_well, well in well_inf.iteritems()
                            if ref_well == ref_img]
                if len(ref_well) != 1:
                    raise MetadataError('Incorrect reference to image files.')
                else:
                    md.well_id = WellPlate.map_well_position_to_id(ref_well[0])
        else:
            raise MetadataError('Incorrect reference to image files.')

        return complemented_metadata

    def determine_missing_basic_metadata(self, metadata):
        '''
        Determine, which of the required basic metadata information, such as
        channel names or time point identifiers could not yet been retrieved.

        Parameters
        ----------
        metadata: List[ChannelMetadata]
            image metadata

        Returns
        -------
        Set[str]
            names of missing basic metadata attributes

        See also
        --------
        `tmlib.metadata.ChannelImageMetadata.INITIALLY_REQUIRED`_
        '''
        missing_metadata = set()
        for i, md in enumerate(metadata):
            for attr in ChannelImageMetadata.BASIC:
                if not hasattr(md, attr):
                    missing_metadata.update(attr)
        return missing_metadata

    def format_metadata_from_filenames(self, metadata, regex):
        '''
        Retrieve metadata from the image filenames using a regular expression.

        For details on how to build a named regular expression
        please refer to documentation of `re` package for
        `regular expression syntax <https://docs.python.org/2/library/re.html#regular-expression-syntax>`_.

        Expressions can be tested conveniently online at `pythex.org <http://pythex.org/>`_.
        This is an
        `example <http://pythex.org/?regex=(%3FP%3Ccycle_name%3E%5B%5E_%5D%2B)_(%3FP%3Cwel_idl%3E%5Cw%2B)_T(%3FP%3Ctime_id%3E%5Cd%2B)F(%3FP%3Csite_id%3E%5Cd%2B)L%5Cd%2BA%5Cd%2BZ(%3FP%3Cplane_id%3E%5Cd%2B)C(%3FP%3Cchannel_name%3E%5Cd%2B)%5C.&test_string=150820-Testset-CV-2_D03_T0001F001L01A01Z01C02.tif&ignorecase=0&multiline=0&dotall=0&verbose=0>`_
        of a named regular expression string for retrieval of information from
        an image filename generated by the Yokogawa CellVoyager microscope.

        Parameters
        ----------
        metadata: List[ChannelImageMetadata]
            metadata for each image
        regex: str
            named regular expression
        '''
        complemented_metadata = list(metadata)  # copy
        if not regex:
            regex = self.REGEX
        provided_names = re.findall(r'\(\?P\<(\w+)\>', regex)
        if not provided_names:
            raise RegexpError('No group names could be found in regular '
                              'expression "%s"' % regex)
        logger.info('provided names for retrieval of metadata from filenames:'
                    ' "%s"' % '", "'.join(provided_names))

        for i, ffm in enumerate(self.file_mapper):
            match = re.search(regex, ffm.filename)
            if not match:
                raise RegexpError(
                        'Metadata could not be retrieved from filename "%s" '
                        'using regular expression "%s"'
                        % (ffm.filename, regex))
            numbers = {'site_id', 'time_id', 'plane_id'}
            for name in provided_names:
                capture = match.group(name)
                if name in numbers:
                    capture = int(capture)
                setattr(complemented_metadata[i], name, capture)

        return complemented_metadata

    def add_user_metadata(self, metadata):
        '''
        Complement metadata with information provided by the user.

        Parameters
        ----------
        metadata: List[ChannelImageMetadata]
            metadata for each channel plane

        Returns
        -------
        List[ChannelImageMetadata]
            complemented image metadata

        Returns
        -------
        List[ChannelImageMetadata]
            complemented metadata
        '''
        print 'TODO'
        # TODO: give user the opportunity to fill in missing data manually
        # e.g. via a csv file

    @staticmethod
    def _calculate_coordinates(positions):
        coordinates = stitch.calc_grid_coordinates_from_positions(positions)
        return coordinates

    def determine_grid_coordinates_from_positions(self, metadata):
        '''
        Determine the coordinates of each image acquisition site within the
        overall continuous acquisition grid (slide or well in a plate)
        based on the absolute microscope stage positions.

        Parameters
        ----------
        metadata: List[ChannelImageMetadata]
            metadata for each channel plane

        Returns
        -------
        List[ChannelImageMetadata]
            complemented metadata

        Raises
        ------
        MetadataError
            when metadata has no "position" attribute or when its value is
            ``None``

        See also
        --------
        `illuminati.stitch.calc_grid_coordinates_from_positions`_
        '''
        # Retrieve the stage positions for each pixel array.
        if (not any([hasattr(md, 'stage_position') for md in metadata])
                or not any(utils.flatten([md.stage_position for md in metadata]))):
            raise MetadataError('Metadata requires "stage_position" attribute '
                                'for determination of grid coordinates.')

        logger.info('translate absolute microscope stage positions into '
                    'relative acquisition grid coordinates')
        complemented_metadata = list(metadata)

        all_positions = list()
        if metadata[0].well_id:
            # group metadata per well
            wells = list(set([md.well_id for md in metadata]))
            for w in wells:
                positions = {
                    i: md.stage_position
                    for i, md in enumerate(metadata) if md.well_id == w
                }
                all_positions.append(positions)

        else:
            positions = {
                i: md.stage_position
                for i, md in enumerate(metadata)
            }
            all_positions.append(positions)

        # all positional indices are one-based!
        for grid in all_positions:
            index, positions = grid.keys(), grid.values()
            coordinates = self._calculate_coordinates(positions)
            for i in xrange(len(index)):
                complemented_metadata[index[i]].row_index = coordinates[i][0]
                complemented_metadata[index[i]].col_index = coordinates[i][1]
        # create globally unique position identifier numbers
        pos = [
            (md.well_id, md.row_index, md.col_index)
            for md in complemented_metadata
        ]
        sites = [sorted(list(set(pos))).index(s) for s in pos]
        for i, s in enumerate(sites):
            complemented_metadata[i].site_id = s+1

        return complemented_metadata

    def determine_grid_coordinates_from_layout(self, metadata,
                                               stitch_layout,
                                               stitch_major_axis,
                                               stitch_dimensions=None):
        '''
        Determine the coordinates of each image acquisition site within the
        overall continuous acquisition grid (slide or well in a plate)
        based on a provided layout.

        Parameters
        ----------
        metadata: List[ChannelImageMetadata]
            metadata for each plane

        Returns
        -------
        List[ChannelImageMetadata]
            complemented metadata

        See also
        --------
        `illuminati.stitch.guess_stitch_dimensions`_
        `illuminati.stitch.calc_grid_coordinates_from_layout`_
        '''
        complemented_metadata = list(metadata)

        all_coordinates = list()
        if metadata[0].well_id:
            # group metadata per well
            wells = list(set([md.well_id for md in metadata]))
            for w in wells:
                indices = [
                    i for i, md in enumerate(metadata) if md.well_id == w
                ]
                if not any(stitch_dimensions):
                    n_sites = len(set(indices))
                    stitch_dimensions = stitch.guess_stitch_dimensions(
                                            n_sites, stitch_major_axis)
                coordinates = stitch.calc_grid_coordinates_from_layout(
                                            stitch_dimensions, stitch_layout)
                all_coordinates.append(dict(zip(indices, coordinates)))
        else:
            indices = range(len(metadata))
            if not any(stitch_dimensions):
                n_sites = len(set(indices))
                stitch_dimensions = stitch.guess_stitch_dimensions(
                                        n_sites, stitch_major_axis)
            coordinates = stitch.calc_grid_coordinates_from_layout(
                                        stitch_dimensions, stitch_layout)
            all_coordinates.append(dict(zip(indices, coordinates)))

        for grid in all_coordinates:
            index, coordinates = grid.keys(), grid.values()
            for i in xrange(len(index)):
                complemented_metadata[index[i]].row_index = coordinates[i][0]
                complemented_metadata[index[i]].col_index = coordinates[i][1]

        # create globally unique position identifier numbers
        pos = [
            (md.well_id, md.row_index, md.col_index)
            for md in complemented_metadata
        ]
        sites = [sorted(list(set(pos))).index(s) for s in pos]
        for i, s in enumerate(sites):
            complemented_metadata[i].site_id = s

        return complemented_metadata

    def build_image_filenames(self, metadata, image_file_format_string):
        '''
        Build unique filenames for the extracted images based on a format
        string  the extracted metadata.

        Since the number of extracted images may be different than the number
        of uploaded image files (because each image file can contain several
        planes), we have to come up with names for the corresponding files.

        Parameters
        ----------
        metadata: List[ChannelImageMetadata]
            metadata for each plane

        Returns
        -------
        List[ChannelImageMetadata]
            metadata, where "name" attribute has been set

        See also
        --------
        `tmlib.cfg`_
        '''
        for i, md in enumerate(metadata):
            fn = md.serialize()
            fn.update({'experiment_name': self.experiment_name})
            md.name = image_file_format_string.format(**fn)
            self.file_mapper[i].name = md.name
        return metadata

    def create_channel_ids(self, metadata):
        '''
        Create for each channel a zero-based unique identifier number.

        Parameters
        ----------
        metadata: List[ChannelImageMetadata]
            metadata for each plane

        Returns
        -------
        List[ChannelImageMetadata]
            metadata, where "channel_id" attribute has been set

        Note
        ----
        The id may not reflect the order in which the channels were acquired
        on the microscope.
        '''
        channels = sorted(set([md.channel_name for md in metadata]))
        for md in metadata:
            for i, c in enumerate(channels):
                if md.channel_name == c:
                    md.channel_id = i
        return metadata

    def create_plane_ids(self, metadata):
        '''
        Create for each focal plane a zero-based unique identifier number.

        Parameters
        ----------
        metadata: List[ChannelImageMetadata]
            metadata for each plane

        Returns
        -------
        List[ChannelImageMetadata]
            metadata, where "time_id" attribute has been set

        Note
        ----
        The id may not reflect the order in which the planes were acquired
        on the microscope.
        '''
        planes = sorted(set([md.plane_id for md in metadata]))
        for md in metadata:
            for i, p in enumerate(planes):
                if md.plane_id == p:
                    md.plane_id = i
        return metadata


    def create_file_hashmap(self, metadata):
        '''
        Create a hashmap for the extraction of individual planes from the
        original image files.

        Parameters
        ----------
        metadata: List[ChannelImageMetadata]
            metadata for each plane

        Returns
        -------
        Dict[str, Dict[str, List[str]]]
            key-value pairs to map the original image filename to the
            *name* of each extracted image and the *series* and *plane*,
            which specify the location in the original file, from where the
            image plane should be extracted
        '''
        hashmap = dict()
        filenames = [ffm.filename for ffm in self.file_mapper]
        series = [ffm.series for ffm in self.file_mapper]
        planes = [ffm.planes for ffm in self.file_mapper]
        for f in set(filenames):
            ix = utils.indices(filenames, f)
            for i in ix:
                hashmap[f] = defaultdict(list)
                hashmap[f]['name'].append(metadata[i].name)
                hashmap[f]['id'].append(metadata[i].id)
                hashmap[f]['series'].append(series[i])
                hashmap[f]['plane'].append(planes[i])

        return hashmap


class DefaultMetadataHandler(MetadataHandler):

    '''
    Class for handling image metadata in standard cases where additional
    metadata files are not required or not available.
    '''

    REGEX = ''

    def __init__(self, image_files, additional_files, ome_xml_files,
                 experiment_name):
        '''
        Initialize an instance of class MetadataHandler.

        Parameters
        ----------
        image_upload_files: List[str]
            full paths to image files
        additional_files: List[str]
            full paths to additional microscope-specific metadata files
        ome_xml_files: List[str]
            full paths to the XML files that contain the extracted OMEXML data
        experiment_name: str
            name of the cycle, i.e. the name of the folder of the corresponding
            experiment or subexperiment
        '''
        super(DefaultMetadataHandler, self).__init__(
                image_files, additional_files, ome_xml_files, experiment_name)
        self.image_files = image_files
        self.additional_files = additional_files
        self.ome_xml_files = ome_xml_files
        self.experiment_name = experiment_name

    @property
    def ome_additional_metadata(self):
        '''
        Returns
        -------
        bioformats.omexml.OMEXML
            empty object
        '''
        self._ome_additional_metadata = bioformats.OMEXML()
        return self._ome_additional_metadata


class DefaultMetadataReader(MetadataReader):

    '''
    `Python-bioformats <https://github.com/CellProfiler/python-bioformats>`_
    provides an interface for reading metadata form files
    using `python-javabridge <https://github.com/CellProfiler/python-javabridge>`_.

    However, this approach often leads to incorrect parsing of metadata.
    Therefore, we decided to extract metadata from the image files directly via
    Bio-Formats using the
    `showinf <http://www.openmicroscopy.org/site/support/bio-formats5.1/users/comlinetools/display.html>`_
    command line tool. This tool prints the OME-XML to standard output, which
    we direct to a file.
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
        NotSupportedError
            when the file format is not supported
        '''
        # ome_xml_data = bf.get_omexml_metadata(filename)
        with open(filename, 'r') as f:
            ome_xml_data = f.read()
        metadata = bioformats.OMEXML(ome_xml_data)
        return metadata
