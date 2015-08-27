import os
import re
import sys
import numpy as np
from abc import ABCMeta
from abc import abstractmethod
from abc import abstractproperty
import bioformats
from cached_property import cached_property
from ..utils import read_json
from ..utils import flatten
from .image_reader import BioformatsImageReader
from .metadata_reader import OmeMetadataReader
from ..metadata import ChannelMetadata
from ..illuminati import stitch
from .. import utils
from . import ome
from .. import imageutils
from ..errors import MetadataError
from ..errors import NotSupportedError
from ..plates import WellPlate


class ImageData(object):

    '''
    Abstract base class for image data and associated metadata from
    heterogeneous microscope file formats using the
    `Bio-Formats <http://www.openmicroscopy.org/site/products/bio-formats>`_
    library.

    Original metadata is extracted from image files as OME-XML according to the
    `OME schema <http://www.openmicroscopy.org/Schemas/Documentation/Generated/OME-2015-01/ome.html>`_.

    The metadata that can be automatically retrieved form image files may not
    be sufficient, but may require additional microscope-specific metadata
    files and/or user input.
    
    Pixel arrays stored in image files are ultimately extracted and each array
    is written to a PNG file. On the one hand, this is done to save disk space
    due to (lossless) file compression and on the other hand for downstream
    compatibility, because not many libraries are able to read images from
    the original file formats (often extended TIFF formats).

    The metadata corresponding to the final PNG images are stored in a
    separate JSON file based to a custom schema.
    '''

    __metaclass__ = ABCMeta

    def __init__(self, image_upload_folder, additional_upload_folder,
                 ome_xml_dir, experiment_dir, cfg, subexperiment=''):
        '''
        Initialize an instance of class ImageData.

        Parameters
        ----------
        image_upload_folder: str
            absolute path to directory where uploaded image files are located
        additional_upload_folder: str
            absolute path to directory where uploaded additional metadata files
            are located
        ome_xml_dir: str
            absolute path to directory where extracted ome-xml files are located
        experiment_dir: str
            absolute path to the corresponding experiment folder
        subexperiment: str, optional
            name of the subexperiment
            (only required in case the experiment has subexperiments)
        cfg: Dict[str, str]
            configuration settings

        See also
        --------
        `tmt.config`_
        '''
        self.image_upload_folder = image_upload_folder
        self.additional_upload_folder = additional_upload_folder
        self.ome_xml_dir = ome_xml_dir
        self.experiment_dir = experiment_dir
        self.subexperiment = subexperiment
        self.cfg = cfg

    @property
    def experiment(self):
        '''
        Returns
        -------
        str
            name of the corresponding experiment
        '''
        self._experiment = os.path.basename(self.experiment_dir)
        return self._experiment

    @property
    def supported_formats_file(self):
        '''
        Returns
        -------
        str
            absolute path to the JSON file that specifies which formats
            are supported

        See also
        --------
        `supported_formats.json`_
        '''
        current_dir = os.path.dirname(__file__)
        self._supported_formats_file = os.path.join(current_dir,
                                                    'supported-formats.json')
        return self._supported_formats_file

    @cached_property
    def supported_formats(self):
        '''
        Returns
        -------
        Dict[str, List[str]]
            names of supported formats with the corresponding file extensions
        '''
        self._supported_formats = read_json(self.supported_formats_file)
        return self._supported_formats

    @property
    def supported_extensions(self):
        '''
        Returns
        -------
        Set[str]
            file extensions of supported formats
        '''
        all_extensions = flatten(self.supported_formats.values())
        self._supported_extensions = set(all_extensions)
        return self._supported_extensions

    @cached_property
    def image_files(self):
        '''
        Returns
        -------
        List[str]
            names of image files

        Note
        ----
        To be recognized as an image file, a file must have one of the
        supported file extensions.

        Raises
        ------
        OSError
            when no image files are found
        '''
        files = [f for f in os.listdir(self.image_upload_folder)
                 if os.path.splitext(f)[1] in self.supported_extensions]
        if len(files) == 0:
            raise OSError('No image files founds in folder: %s'
                          % self.image_upload_folder)
        self._image_files = files
        return self._image_files

    @cached_property
    def ome_xml_files(self):
        '''
        Returns
        -------
        List[str]
            names of the XML files that contain the extracted OME-XML data
            (same basename as the corresponding image file,
             but *.xml* extension)

        Raises
        ------
        OSError
            when no ome-xml files are found
        '''
        files = [f for f in os.listdir(self.ome_xml_dir)
                 if f.endswith('.ome.xml')]
        if len(files) == 0:
            raise OSError('No ome-xml files founds in folder: %s'
                          % self.ome_xml_dir)
        self._ome_xml_files = files
        return self._ome_xml_files

    @abstractproperty
    def additional_files(self):
        '''
        Returns
        -------
        List[str] or None
            names of additional microscope-specific metadata files
        '''
        pass

    @property
    def metadata_dir(self):
        '''
        Returns
        -------
        str
            absolute path to the directory, where extracted metadata should be
            stored

        See also
        --------
        `tmt.config`_
        '''
        self._metadata_dir = self.cfg['METADATA_FOLDER_FORMAT'].format(
                                        experiment_dir=self.experiment_dir,
                                        subexperiment=self.subexperiment,
                                        sep=os.path.sep)
        return self._metadata_dir

    @property
    def metadata_file(self):
        '''
        Returns
        -------
        str
            name of the file that contains the metadata for each extracted
            image

        See also
        --------
        `tmt.config`_
        '''
        self._metadata_file = self.cfg['METADATA_FILE_FORMAT'].format(
                                        experiment=self.experiment)
        return self._metadata_file

    @property
    def image_dir(self):
        '''
        Returns
        -------
        str
            absolute path to the directory where extracted images should be
            stored

        See also
        --------
        `tmt.config`_
        '''
        self._image_dir = self.cfg['IMAGE_FOLDER_FORMAT'].format(
                                        experiment_dir=self.experiment_dir,
                                        subexperiment=self.subexperiment,
                                        sep=os.path.sep)
        return self._image_dir

    def read_image_metadata(self):
        '''
        Read the OME-XML metadata extracted from the image files.

        Returns
        -------
        Dict[str, bioformats.omexml.OMEXML]
            metadata retrieved from image files

        See also
        --------
        `metadata_reader.OmeMetadataReader`_
        '''
        self.ome_image_metadata = dict()
        with OmeMetadataReader() as reader:
            for f in self.ome_xml_files:
                filename = os.path.join(self.metadata_dir, f)
                self.ome_image_metadata[f] = reader.read(filename)
        return self.ome_image_metadata

    @staticmethod
    def _create_metadata(ome_image_element):
        '''
        Create an instance of class ChannelMetadata for each channel specified
        in an *OMEXML* *Image* element.

        Parameters
        ----------
        ome_image_element: bioformats.omexml.OMEXML.Image
            *OME* *Image* element

        Returns
        -------
        List[ChannelMetadata]
            metadata objects, one for each channel in `ome_image_element`

        Warning
        -------
        It is assumed that all *Plane* elements of `ome_image_element` where
        acquired at the same site, i.e. microscope stage position.

        Raises
        ------
        NotSupportedError
            when metadata specifies more than one timepoint for the provided
            *Image* element
        '''
        image_metadata = list()
        pixels = ome_image_element.Pixels

        n_timepoints = pixels.SizeT
        if n_timepoints > 1:
            raise NotSupportedError('Only images with a single timepoint '
                                    'are supported.')

        n_planes = pixels.plane_count
        if n_planes == 0:
            # Sometimes an image doesn't have any planes, but still
            # contains multiple channels and/or z-stacks.
            # Let's create new plane elements for consistency.
            pixels = ome.create_channel_planes(pixels)
            n_planes = pixels.plane_count  # update plane count

        n_channels = pixels.SizeC
        for c in xrange(n_channels):
            md = ChannelMetadata()
            md.name = ome_image_element.Name
            md.dtype = pixels.PixelType
            md.dimensions = (pixels.SizeY, pixels.SizeX)
            md.channel_name = pixels.Channel(c).Name
            md.channel_planes = list()
            planes = [pixels.Plane(p) for p in xrange(n_planes)
                      if c == pixels.Plane(p).TheC]
            md.position = (planes[0].PositionY, planes[0].PositionX)
            for p in planes:
                md.channel_planes.append(p)
            image_metadata.append(md)

        return image_metadata

    def format_image_metadata(self, ome_image_metadata):
        '''
        Convert image metadata from *OMEXML* into custom format.

        Parameters
        ----------
        ome_image_metadata: Dict[str, bioformats.omexml.OMEXML]
            *OME* metadata retrieved from each image file

        Returns
        -------
        List[ChannelMetadata]
            formatted metadata objects

        Note
        ----
        There must be one *OMEXML* object for each image file.
        An image file, however, may contain more than one *Image* element,
        which is referred to as a *series*.
        Each *Image*/*Pixels* element contains at least one *Plane* element.
        A *Plane* represents a 2-dimensional pixel array for each channel,
        z-section or timepoint. The different planes are often grouped
        together as a *series* per acquisition site, i.e. microscope stage
        position (but this doesn't have to be the case).
        Ultimately, we would like to create image files that contain only
        a single-channel plane image per file. To this end, we group planes per
        channel. In the simplest case, there is only one plane per
        channel for a given *Image* element. If images were acquired at
        multiple z resolutions, they will be subsequently projected to 2D.
        Multiple timepoints are not supported.

        Raises
        ------
        NotSupportedError
            when metadata specifies more than one timepoint for an *Image*
            element

        See also
        --------
        `metadata.ChannelMetadata`_
        '''
        formatted_metadata = list()
        for f in ome_image_metadata.keys():
            n_series = ome_image_metadata[f].image_count
            # The number of series corresponds to the number of planes
            # within the image file.
            for i in xrange(n_series):
                image = ome_image_metadata[f].image(i)
                md = self._create_metadata(image)
                for m in md:
                    m.orig_filename = f
                    m.series = i
                formatted_metadata.extend(md)

        return formatted_metadata

    @staticmethod
    def _update_metadata(ome_image_element, metadata):
        '''
        Update attribute values of existing instances of class ChannelMetadata.

        Paramters
        ---------
        ome_image_element: bioformats.omexml.OMEXML.Image
            *OME* *Image* element
        metadata: List[ChannelMetadata]
            corresponding metadata objects, one for each channel in
            `ome_image_element`

        Returns
        -------
        List[ChannelMetadata]
            updated custom metadata objects

        Raises
        ------
        AssertionError
            when names or number of channels in `ome_image_element` and the
            number of elements in `image_metadata` are not the same
        '''
        updated_metadata = list(metadata)  # copy
        pixels = ome_image_element.Pixels

        n_planes = pixels.plane_count
        n_channels = pixels.SizeC
        if n_channels is not len(metadata):
            raise AssertionError('Number of channels must be identical.')
        for c in xrange(n_channels):
            md = updated_metadata[c]
            # There should be a naicer way...
            if not md.name:
                try:
                    md.name = ome_image_element.Name
                except:
                    pass
            if not md.dtype:
                try:
                    md.dtype = pixels.PixelType
                except:
                    pass
            if not any(md.dimensions):
                try:
                    md.dimensions = (pixels.SizeY, pixels.SizeX)
                except:
                    pass
            if not md.channel_name:
                try:
                    md.channel_name = pixels.Channel(c).Name
                except:
                    pass
            if not any(md.position):
                try:
                    planes = [pixels.Plane(p) for p in xrange(n_planes)
                              if c == pixels.Plane(p).TheC]
                    md.position = (planes[0].PositionY, planes[0].PositionX)
                except:
                    pass
            updated_metadata[c] = md

        return updated_metadata

    def format_additional_metadata(self, ome_additional_metadata, metadata):
        '''
        Convert additional metadata from *OMEXML* into custom *TissueMAPS*
        format.

        Additional metadata files contain information that is not available
        from individual image files, for example information about wells in
        case of a well plate format. Since these additional files are generally
        microscope-specific and require specialized readers, they are treated
        separately.

        Parameters
        ----------
        ome_additional_metadata: bioformats.omexml.OMEXML
            OME metadata retrieved from additional metadata files
        metadata: List[ChannelMetadata]
            formatted image metadata

        Returns
        -------
        List[ChannelMetadata]
            formatted metadata

        Note
        ----
        Since image-specific information is stored in *Image* elements and
        plate-specific information in the *Plate* element, one has to map
        the well information to individual images. This can be achieved by
        providing references in the *ImageRef* field of *WellSample* elements.
        However, sometimes a direct reference is not possible. In this case,
        we try to match them via the filenames using regular expressions.
        This is of course only possible if well id is encoded in the filenames.

        Warning
        -------
        There must be only one *OMEXML* object for all image files.
        This is in contrast to the metadata for individual images, where there
        is a separate *OMEXML* object for each image file. The
        microscope-specific readers are responsible to ensure that the *image
        count* matches.
        *image count* = *number of channels* x *number of sites*

        Warning
        -------
        *Image* elements with *Name* "default.png" are assumed to be empty
        and they are ignored. They are automatically created by
        `python-bioformats` when *image_count* is set.

        Raises
        ------
        NotSupportedError
            when metadata specifies more than one *Plate* element or more
            than one timepoint for an *Image* element or when *Plane* elements
            have different x, y positions
        MetadataError
            when well ids cannot be mapped to images

        See also
        --------
        `metadata.ChannelMetadata`_
        '''
        complemented_metadata = list(metadata)
        n_images = ome_additional_metadata.image_count
        # The number of images corresponds to the total number of
        # single-channel planes, i.e. the number of final image files that will
        # get extracted from the original image files and saved as PNG files.
        for i in xrange(n_images):
            if ome_additional_metadata.image(i).Name is 'default.png':
                # Setting the image count automatically creates empty image
                # elements with name "default.png". They can be skipped.
                continue
            image = ome_additional_metadata.image(i)
            # TODO: this might be dangerous because it may happen that the
            # name of the image could not be determined or is not provided
            # by the microscope.
            matched_objects = {ix: md for ix, md in enumerate(metadata)
                               if md.name == image.Name}
            updated_objects = self._update_metadata(image,
                                                    matched_objects.values())
            for j, ix in enumerate(matched_objects.keys()):
                complemented_metadata[ix] = updated_objects[j]

        # Is there a *Plate* element specified?
        plates = ome_additional_metadata.plates
        n_plates = len(plates)
        if n_plates == 0:
            for i in xrange(n_images):
                complemented_metadata[i].well = None
        elif n_plates > 1:
            raise NotSupportedError('Only a single plate is supported.')
        n_wells = len(plates[0].Well)
        well_inf = dict()
        for w in xrange(n_wells):
            well_row = plates[0].Well[w].Row
            well_col = plates[0].Well[w].Column
            well_pos = (well_row, well_col)
            if plates[0].RowNamingConvention == 'letter':
                well_pos = WellPlate.well_id_to_position(well_pos)
            names = flatten([s.ImageRef for s in plates[0].Well[w].Sample])
            well_inf.update({n: well_pos for n in names})

        if all(well_inf.keys()):
            for md in complemented_metadata:
                # TODO: check that there is only one!
                md.well = [well for n, well in well_inf.iteritems()
                           if n == md.name][0]
        else:
            # It may be the case that there are no direct reference available.
            # In this case, we try to match wells to images via the filenames
            # using regular expressions.
            if plates[0].RowNamingConvention != 'letter':
                raise MetadataError('Extraction of well ids from filenames '
                                    'is only possible if RowNamingConvention '
                                    'is "letter"')
            regexp_string = '_([A-Z]\d{2})_'
            r = re.compile(regexp_string)
            regexp_match = {f: re.search(r, f) for f in self.image_files}
            if all(regexp_match.values()):
                well_inf = {f: m.group(1) for f, m in regexp_match.iteritems()}
                well_pos = WellPlate.well_id_to_position(well_inf.values())
                filenames = well_inf.keys()
                well_inf = dict(zip(filenames, well_pos))
                for md in complemented_metadata:
                    # TODO: check that there is only one!
                    md.well = [f for f, id in well_inf.iteritems()
                               if f == md.orig_filename][0]
            else:
                raise MetadataError('Well ids could not be determined from '
                                    'filenames using regular expression "%s"'
                                    % regexp_string)

        return complemented_metadata

    def determine_missing_image_metadata(self):
        '''
        Determine, which of the required metadata information is not available.

        Returns
        -------
        List[str]
            names of missing information

        See also
        --------
        `tmt.metadata.ChannelMetadata`_
        '''
        # List comprehension to the max :)
        # Provides the index and the name of the missing information
        missing = [(i, k) for i, md in enumerate(self.image_metadata)
                   for k, v in md.iteritems()
                   if k in ChannelMetadata.required_metadata and v is None]
        self.missing_metadata = missing
        return self.missing_metadata

    @abstractmethod
    def read_additional_metadata(self):
        '''
        Read additionally required metadata not provided with the image files.
        These files and the corresponding readers are microscope specific
        and have to be provided in a subclass inheriting from this base class.

        Returns
        -------
        bioformats.omexml.OMEXML
            metadata retrieved from additional microscope specific files
        '''
        pass

    def complement_image_metadata(self):
        '''
        Complement missing image metadata with additional metdata
        (if available).

        Returns
        -------
        bioformats.omexml.OMEXML
            combined metadata
        '''
        available = [(i, k) for i, md in enumerate(self.missing_metadata)
                     for k in md if self.additional_metadata[i][k]]
        for i, k in available:
            self.metadata[i][k] = self.additional_metadata[i][k]
        return self.metadata

    # TODO: user input

    def determine_grid_coordinates(self):
        '''
        Determine the position of each image acquisition site relative to its
        corresponding acquisition grid (slide or well in a plate).
        To this end, calculate the relative positions (coordinates) of images
        within each acquisition grid based on the absolute stage positions.

        See also
        --------
        `illuminati.stitch.calc_image_coordinates`_
        '''
        # Retrieve the stage positions for each pixel array.
        all_positions = list()
        if self.metadata.values()[0].well:
            wells = list(set([md.well for md in self.metadata.values()]))
            for w in wells:
                positions = {i: md.position
                             for i, md in enumerate(self.metadata.values())
                             if md.well == w}
                all_positions.append(positions)

        else:
            positions = {i: md.position
                         for i, md in enumerate(self.metadata.values())}
            all_positions.append(positions)

        count = 0
        for p in all_positions:
            index, positions = p.keys(), p.values()
            # Calculate the relative coordinates for each unique pair
            # of stage positions.
            unique_positions = list(set(positions))
            unique_index = [unique_positions.index(p) for p in positions]
            unique_coords = stitch.calc_image_coordinates(unique_positions)
            # Map the unique coordinates back.
            coordinates = [unique_coords[i] for i in unique_index]
            for i in xrange(len(index)):
                # All positional indices are one-based!
                count += 1
                self.metadata[i].site = count
                self.metadata[i].row = coordinates[i][0]
                self.metadata[i].column = coordinates[i][1]

    def extract_images(self):
        with BioformatsImageReader() as reader:
            for md in self.metadata:
                for c, plane in enumerate(md.channel_planes):
                    # Perform maximum intensity projection to reduce
                    # dimensionality to 2D if there is more than 1 z-stack
                    stack = np.empty((md.dimensions[0],
                                      md.dimensions[1], len(plane)),
                                     dtype=md.dtype)
                    for z, p in enumerate(plane):
                        f_path = os.path.join(self.upload_folder,
                                              md.orig_filename)
                        stack[:, :, z] = reader.read_image(f_path,
                                                           index=p,
                                                           series=md.series,
                                                           rescale=False)
                    plane_pixels = np.max(stack, axis=2)
                    # Write plane (2D single-channel image) to file
                    image_file = self.cfg['IMAGE_FILE_FORMAT'].format(
                                            experiment=self.experiment,
                                            cycle=1,
                                            site=md.site,
                                            channel=c,
                                            suffix='.png')
                    filename = os.path.join(self.image_dir, image_file)
                    imageutils.save_image(plane_pixels, filename)

    def write_metadata_to_file(self):
        '''
        Write serialized metadata to JSON file.
        '''
        data = dict()
        for md in self.metadata:
            data[md.filename] = md.serialize()
        filename = os.path.join(self.metadata_dir, self.metadata_file)
        utils.write_json(filename, data)


class OmeImageData(ImageData):

    def __init__(self, image_upload_folder, additional_upload_folder,
                 ome_xml_dir, experiment_dir, cfg, subexperiment=''):
        super(OmeImageData, self).__init__(image_upload_folder,
                                           additional_upload_folder,
                                           ome_xml_dir,
                                           experiment_dir, cfg, subexperiment)
        self.image_upload_folder = image_upload_folder
        self.additional_upload_folder = additional_upload_folder
        self.ome_xml_dir = ome_xml_dir
        self.experiment_dir = experiment_dir
        self.subexperiment = subexperiment
        self.cfg = cfg

    @property
    def additional_files(self):
        '''
        Returns
        -------
        None
        '''
        self._additional_files = None
        return self._additional_files

    def read_additional_metadata(self):
        '''
        Returns
        -------
        bioformats.omexml.OMEXML
            empty object
        '''
        self.additional_metadata = bioformats.OMEXML()
        return self.additional_metadata

    def extract_metadata_from_additional_files(self):
        pass
