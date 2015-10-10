import os
import re
import bioformats
import logging
from natsort import natsorted
from collections import defaultdict
from cached_property import cached_property
from abc import ABCMeta
from abc import abstractproperty
from ..metadata import ImageFileLayout
from ..illuminati import stitch
from .. import utils
from ..errors import MetadataError
from ..errors import NotSupportedError
from ..errors import RegexpError
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
                 experiment_name, plate_dimensions):
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
        plate_dimensions: Tuple[int]
            number of rows and column in the plate
        '''
        self.image_files = image_files
        self.additional_files = additional_files
        self.ome_xml_files = ome_xml_files
        self.experiment_name = experiment_name
        self.plate_dimensions = plate_dimensions
        self.metadata = bioformats.OMEXML()
        self.file_mapper = list()
        self.id_to_image_ix_lut = dict()
        self.id_to_wellsample_ix_lut = dict()
        self.channels = set()
        self.planes = set()
        self.time_points = set()

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

    def configure_ome_metadata_from_image_files(self):
        '''
        Collect image metadata from individual `OMEXML` elements (one for each
        original image file) and combine them into a single `OMEXML` element
        with n single-plane *Image* elements, where n is the number of final
        image files.

        Returns
        -------
        bioformats.OMEXML
            metadata with an image element for each ultimately extracted image

        Note
        ----
        An original image file may contain more than one *Image* element,
        which is referred to as a *Series*.
        Each *Image*/*Pixels* element contains at least one *Plane* element.
        A *Plane* represents a 2-dimensional pixel array for a given channel,
        z-section and time point. The different planes are generally grouped
        together as a *Series* per acquisition site, i.e. microscope stage
        position.
        Ultimately, we would like to create image files that contain only
        a single plane per file for each channel, time point and z position.
        To this end, the metadata hierarchy gets flattened, i.e. a separate
        *Image* element will be created for each original *Plane* element.
        '''
        logger.info('format OMEXML metadata')
        count = 0
        # NOTE: The order of files is important for some metadata information!
        filenames = natsorted(self.ome_image_metadata.keys())
        for i, f in enumerate(filenames):
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

                # if keep_stacks:
                #     stacks = [[pixels.Plane(x)] for x in xrange(n_planes)]
                # else:
                #     stacks = list()
                #     # Group all focal planes in the image together to a z-stack
                #     tpoints = [pixels.Plane(x).TheT for x in xrange(n_planes)]
                #     channels = [pixels.Plane(x).TheC for x in xrange(n_planes)]
                #     for t in set(tpoints):
                #         for c in set(channels):
                #             stacks.append([
                #                 pixels.Plane(x) for x in xrange(n_planes)
                #                 if pixels.Plane(x).TheT == t
                #                 and pixels.Plane(x).TheC == c
                #             ])

                # Each metadata element represents an image, which could
                # correspond to an individual plane or a z-stack, i.e. a
                # collection of several focal planes with the same channel
                # and time point.
                # for p, stack in enumerate(stacks):
                for p in xrange(n_planes):
                    plane = pixels.Plane(p)
                    # Create a separate *Image*/*Pixels* for each *Plane*
                    # in the original image file
                    if count == 0:
                        # There is already one image created by default
                        new_img = self.metadata.image(count)
                    else:
                        self.metadata.set_image_count(count+1)
                        new_img = self.metadata.image(count)
                    # new_img.ID = str(count)
                    new_img.Name = image.Name
                    pxl = new_img.Pixels
                    pxl.plane_count = 1
                    pxl.Channel(0).Name = pixels.Channel(plane.TheC).Name  # TODO
                    if pxl.Channel(0).Name is not None:
                        self.channels.add(pxl.Channel(0).Name)
                    pxl.PixelType = pixels.PixelType
                    pxl.SizeX = pixels.SizeX
                    pxl.SizeY = pixels.SizeY
                    # Each new *Image* will only contain a single *Plane*
                    pxl.SizeT = 1
                    pxl.SizeC = 1
                    pxl.SizeZ = 1
                    pln = pxl.Plane(0)
                    pln.TheT = plane.TheT
                    self.time_points.add(pln.TheT)
                    pln.TheC = 0  # TODO: later
                    pln.PositionX = plane.PositionX
                    pln.PositionY = plane.PositionY

                    # Create a lookup table that will make it easier later on
                    # to retrieve the image given an ID
                    self.id_to_image_ix_lut[new_img.ID] = count

                    # if len(stack) > 1:
                    #     pln.TheZ = 0
                    # else:
                    #     pln.TheZ = plane.TheZ
                    pln.TheZ = plane.TheZ
                    self.planes.add(pln.TheZ)

                    fm = ImageFileLayout()
                    fm.name = new_img.Name
                    fm.filename = f
                    fm.series = s
                    # # Group planes in case of projection
                    # if len(stack) > 1:
                    #     fm.planes = range(len(stack))
                    # else:
                    #     fm.planes = [p]
                    fm.planes = [p]

                    self.file_mapper.append(fm)
                    count += 1

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

    def _update_metadata(self, ome_image_element, metadata):
        # NOTE: The parameter "metadata" is a list of OME *Image* objects.
        updated_metadata = list(metadata)
        pixels = ome_image_element.Pixels

        n_channels = pixels.SizeC
        n_timepoints = pixels.SizeT
        n_planes = pixels.SizeZ
        n_total = n_channels * n_timepoints * n_planes
        if n_total is not len(metadata):
            raise AssertionError('Images mustn\'t have more than one plane.')
        for c in xrange(n_channels):
            img = metadata[c]
            if not img.Pixels.Channel(0).Name:
                try:
                    img.Pixels.Channel(0).Name = pixels.Channel(c).Name
                    self.channels.add(img.Pixels.Channel(0).Name)
                except AttributeError:
                    pass
            if not(hasattr(img.Pixels.Plane(0), 'PositionX')
                   and hasattr(img.Pixels.Plane(0), 'PositionY')):
                try:
                    img.Pixels.Plane(0).PositionX = pixels.Plane(0).PositionX
                    img.Pixels.Plane(0).PositionY = pixels.Plane(0).PositionY
                except AttributeError:
                    pass
            updated_metadata[c] = img

        return updated_metadata

    def configure_ome_metadata_from_additional_files(self):
        '''
        Convert *OMEXML* metadata retrieved form additional microscope-specific
        metadata files into custom format and add it the metadata retrieved
        from image files.

        Additional metadata files contain information that is not available
        from individual image files, for example information about wells.

        Returns
        -------
        bioformats.OMEXML
            metadata with an image element for each ultimately extracted image

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
        and consequently skipped, i.e. their metadata content is not updated.

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
        `tmlib.metaconfig.default.MetaDataHandler`_
        `tmlib.metaconfig.visiview.VisiviewMetaDataHandler`_
        `tmlib.metaconfig.cellvoyager.CellvoyagerMetaDataHandler`_
        '''
        if self.ome_additional_metadata.image_count == 1:
            # One image is always added by default.
            logger.info('No additional metadata provided')

            # In any case, there has to be one *Plate* element.
            n_plates = len(self.ome_additional_metadata.plates)
            if n_plates == 0:
                raise MetadataError('No plate information provided.')
            elif n_plates > 1:
                raise NotSupportedError('Only one plate per experiment.')
            return self.metadata

        if not self.regex:
            raise RegexpError('No regular expression available.')

        # NOTE: The value of the "image_count" attribute must equal the
        # total number of planes.
        n_images = self.ome_additional_metadata.image_count
        if not n_images == self.metadata.image_count:
            raise MetadataError('Incorrect number of images.')

        plate = self.ome_additional_metadata.plates[0]

        lut = dict()
        r = re.compile(self.regex)
        for i in xrange(n_images):
            # Individual image elements need to be mapped to well sample
            # elements in the well plate. The custom handlers provide a
            # regular expression, which is supposed to match a pattern in the
            # image file name and is able to extract the required information
            # Here we create a lookup table with a mapping of captured matches
            # to the ID of the corresponding image element.
            filename = os.path.basename(self.file_mapper[i].filename)
            match = r.search(filename)
            if not match:
                raise MetadataError(
                        'Incorrect reference to image files in plate element.')
            captures = match.groupdict()
            if 'z' not in captures.keys():
                captures['z'] = self.metadata.image(i).Pixels.Plane(0).TheZ
            index = sorted(captures.keys())
            key = tuple([captures[ix] for ix in index])
            lut[key] = self.metadata.image(i).ID

            # Update metadata with information provided from additional files.
            # NOTE: Only image elements are considered for which the value
            # of the *Name* attribute matches.
            if self.ome_additional_metadata.image(i).Name == 'default.png':
                continue
            image = self.ome_additional_metadata.image(i)
            matched_elements = {
                ix: self.metadata.image(ix)
                for ix, fm in enumerate(self.file_mapper)
                if fm.name == image.Name
            }
            updated_elements = self._update_metadata(
                                    image, matched_elements.values())
            for j, ix in enumerate(matched_elements.keys()):
                img = self.metadata.image(ix)
                img = updated_elements[j]

        # NOTE: Plate information is usually not readily available from images
        # or additional metadata files and thus requires custom readers/handlers
        new_plate = self.metadata.PlatesDucktype(
                        self.metadata.root_node).newPlate(name='plate')
        new_plate.RowNamingConvention = plate.RowNamingConvention
        new_plate.ColumnNamingConvention = plate.ColumnNamingConvention
        new_plate.Rows = plate.Rows
        new_plate.Columns = plate.Columns

        n_wells = len(plate.Well)
        for w in xrange(n_wells):
            new_well = self.metadata.WellsDucktype(new_plate).new(
                            row=plate.Well[w].Row, column=plate.Well[w].Column)
            new_samples = self.metadata.WellSampleDucktype(new_well.node)
            n_samples = len(plate.Well[w].Sample)
            for s in xrange(n_samples):
                new_samples.new(index=s)
                # Find the reference *Image* elements for the current
                # well sample using the above created lookup table
                # (using the same sorting logic!)
                reference = plate.Well[w].Sample[s].ImageRef
                index = sorted(reference.keys())
                key = tuple([reference[ix] for ix in index])
                new_samples[s].ImageRef = lut[key]
                self.id_to_wellsample_ix_lut[lut[key]] = new_samples[s].Index

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
        missing_metadata = set()
        if not self.channels or any([c is None for c in self.channels]):
            missing_metadata.add('channel')
        if not self.planes:
            missing_metadata.add('focal plane')
        if not self.time_points:
            missing_metadata.add('time point')
        if not hasattr(self.metadata, 'Plate'):
            missing_metadata.add('plate')
        return missing_metadata

    def configure_metadata_from_filenames(self, regex=None):
        '''
        Configure metadata based on information encoded in image filenames
        using a regular expression with named groups::
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
        regex: str
            named regular expression

        Returns
        -------
        bioformats.OMEXML
            metadata with an image element for each ultimately extracted image
        '''
        if not regex:
            regex = self.REGEX
        if not regex:
            raise RegexpError('No regular expression provided.')

        provided_names = re.findall(r'\(\?P\<(\w+)\>', regex)
        required_names = {'w', 'c', 'z', 's', 't'}
        for name in provided_names:
            if name not in required_names:
                raise RegexpError(
                    '"%s" is not a supported group name.\n Supported are "%s"'
                    % (name, '", "'.join(required_names)))

        for name in required_names:
            if name not in provided_names:
                raise RegexpError('Missing required group name "%s"', name)

        logger.info('retrieve metadata from filenames via regular expression')
        logger.debug('expression: %s', regex)

        wells = defaultdict(list)
        r = re.compile(regex)
        for i, fm in enumerate(self.file_mapper):
            img = self.metadata.image(i)
            match = r.search(fm.filename)
            if not match:
                raise RegexpError(
                        'Metadata could not be retrieved from filename "%s" '
                        'using regular expression "%s"'
                        % (fm.filename, regex))
            capture = match.groupdict()
            img.Pixels.Channel(0).Name = capture['c']
            img.Pixels.Plane(0).TheZ = capture['z']
            img.Pixels.Plane(0).TheT = capture['t']
            # Collect well and site information
            wells[capture['w']].append(capture['s'])

        logger.info('build well plate element based on information '
                    'retrieved from filenames')

        # Build a well plate description based on "well" and "site" information
        plate = self.ome_additional_metadata.plates[0]
        plate.RowNamingConvention = 'letter'
        plate.ColumnNamingConvention = 'number'
        plate.Rows = self.plate_dimensions[0]
        plate.Columns = self.plate_dimensions[1]
        well_ids = wells.keys()
        if not(utils.is_number(well_ids[0][1:]) and well_ids[0][0].isupper()):
            raise MetadataError('Plate naming convention is not understood.')
        for w in well_ids:
            row = utils.map_letter_to_number(w[0])
            col = int(w[1:])
            well = self.metadata.WellsDucktype(plate).new(row=row, column=col)
            well_samples = self.metadata.WellSampleDucktype(well.node)
            for i, site in enumerate(wells[w]):
                well_samples.new(index=i)
                well_samples[i].ImageRef = self.metadata.image(i).ID

        return self.metadata

    def add_user_metadata(self):
        '''
        Complement metadata with information provided by the user.

        Returns
        -------
        bioformats.OMEXML
            metadata with an image element for each ultimately extracted image
        '''
        print 'TODO'
        # TODO: give user the opportunity to fill in missing data manually
        # e.g. via a csv file

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
        bioformats.OMEXML
            metadata with an image element for each ultimately extracted image

        Raises
        ------
        MetadataError
            when stage position information is not available from `metadata`

        See also
        --------
        `illuminati.stitch.calc_grid_coordinates_from_positions`_
        '''
        # Retrieve the stage positions for each pixel array.
        positions = list()
        for i in xrange(self.metadata.image_count):
            img = self.metadata.image(i)
            p = img.Pixels.Plane(0)
            if (not(hasattr(p, 'PositionY')) or p.PositionY is None
                    or not(hasattr(p, 'PositionX')) or p.PositionX is None):
                raise MetadataError(
                    'Stage position information is not available for image: %s'
                    % img.Name)

        logger.info('translate absolute microscope stage positions into '
                    'relative acquisition grid coordinates')

        plate = self.metadata.plates[0]
        for w in plate.Well:

            well = plate.Well[w]

            positions = list()
            for i, sample in enumerate(well.Sample):

                ix = self.id_to_image_ix_lut[sample.ImageRef]
                plane = self.metadata.image(ix).Pixels.Plane(0)
                pos = (plane.PositionY, plane.PositionX)
                positions.append(pos)

            coordinates = self._calculate_coordinates(positions)

            for i, sample in enumerate(well.Sample):
                sample.PositionY = coordinates[i][0]
                sample.PositionX = coordinates[i][1]

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
        bioformats.OMEXML
            metadata with an image element for each ultimately extracted image

        See also
        --------
        `illuminati.stitch.guess_stitch_dimensions`_
        `illuminati.stitch.calc_grid_coordinates_from_layout`_
        '''
        plate = self.metadata.plates[0]

        for w in plate.Well:

            well = plate.Well[w]
            n_samples = len(well.Sample)

            if not any(stitch_dimensions):
                stitch_dimensions = stitch.guess_stitch_dimensions(
                                        n_samples, stitch_major_axis)

            coordinates = stitch.calc_grid_coordinates_from_layout(
                                        stitch_dimensions, stitch_layout)

            for i, sample in enumerate(well.Sample):
                sample.PositionY = coordinates[i][0]
                sample.PositionX = coordinates[i][1]

        # # create globally unique position identifier numbers
        # pos = [
        #     (pm.well_id, pm.row_index, pm.col_index)
        #     for pm in self.position_mapper
        # ]
        # sites = [sorted(list(set(pos))).index(s) for s in pos]
        # for i, s in enumerate(sites):
        #     self.position_mapper[i].site_id = s

        return self.metadata

    def update_channel_ids(self):
        '''
        Create for each channel a zero-based unique identifier number.

        Returns
        -------
        bioformats.OMEXML
            metadata with an image element for each ultimately extracted image

        Note
        ----
        The id may not reflect the order in which the channels were acquired
        on the microscope.
        '''
        for i in xrange(self.metadata.image_count):
            for j, c in enumerate(self.channels):
                if self.metadata.image(i).Pixels.Channel(0).Name == c:
                    self.metadata.image(i).Pixels.Plane(0).TheC = j
        return self.metadata

    def update_plane_ids(self):
        '''
        Create for each focal plane a zero-based unique identifier number.

        Returns
        -------
        List[ChannelImageMetadata]
            metadata, where "time_id" attribute has been set

        Note
        ----
        The id may not reflect the order in which the planes were acquired
        on the microscope.
        '''
        planes = sorted(set([
            self.metadata.image(i).Pixels.Plane(0).TheZ
            for i in xrange(self.metadata.image_count)
        ]))
        for i in xrange(self.metadata.image_count):
            for j, p in enumerate(planes):
                if self.metadata.image(i).Pixels.Plane(0).TheZ == p:
                    self.metadata.image(i).Pixels.Plane(0).TheZ = j
        return self.metadata

    def build_image_filenames(self, image_file_format_string):
        '''
        Build unique filenames for the extracted images based on a format
        string  the extracted metadata.

        Since the number of extracted images may be different than the number
        of uploaded image files (because each image file can contain several
        planes), we have to come up with names for the corresponding files.

        Parameters
        ----------
        image_file_format_string: str
            Python format string

        Returns
        -------
        bioformats.OMEXML
            metadata with an image element for each ultimately extracted image

        See also
        --------
        `tmlib.cfg`_
        '''
        for i in xrange(self.metadata.image_count):
            fieldnames = {
                'experiment_name': self.experiment_name,
                'site_id': self.position_mapper[i].site_id,
                'channel_id': self.metadata.image(i).Channel(0).Name,
                'plane_id': self.metadata.image(i).Pixels.Plane(0).TheZ,
                'time_id': self.metadata.image(i).Pixels.Plane(0).TheT
            }
            new_name = image_file_format_string.format(**fieldnames)
            self.metadata.image(i).Name = new_name
            self.file_mapper[i].name = new_name
        return self.metadata

    def create_image_hashmap(self):
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
        hashmap = dict()
        filenames = [fm.filename for fm in self.file_mapper]
        series = [fm.series for fm in self.file_mapper]
        planes = [fm.planes for fm in self.file_mapper]
        for f in set(filenames):
            ix = utils.indices(filenames, f)
            for i in ix:
                hashmap[f] = defaultdict(list)
                hashmap[f]['name'].append(self.metadata.image(i).Name)
                hashmap[f]['id'].append(self.metadata.image(i).ID)
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
                 experiment_name, plate_dimensions):
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
            name of the corresponding experiment
        plate_dimensions: Tuple[int]
            number of rows and column in the plate
        '''
        super(DefaultMetadataHandler, self).__init__(
                image_files, additional_files, ome_xml_files,
                experiment_name, plate_dimensions)
        self.image_files = image_files
        self.additional_files = additional_files
        self.ome_xml_files = ome_xml_files
        self.experiment_name = experiment_name
        self.plate_dimensions = plate_dimensions

    @property
    def ome_additional_metadata(self):
        '''
        Returns
        -------
        bioformats.omexml.OMEXML
            empty object
        '''
        self._ome_additional_metadata = bioformats.OMEXML()
        # Add an empty *Plate* element
        self._ome_additional_metadata.PlatesDucktype(
                    self._ome_additional_metadata.root_node).newPlate(
                    name='default')
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
