import os
import re
import numpy as np
import bioformats as bf
import subprocess
from abc import ABCMeta
from abc import abstractmethod
from abc import abstractproperty
# from cached_property import cached_property
from ..reader import BioformatsMetadataReader
from ..reader import BioformatsImageReader
from ..reader import YokogawaMetadataReader
from ..reader import VisitronMetadataReader
from ..metadata import ChannelMetadata
from ..illuminati import stitch
from .. import utils
from . import imageutils
from . import ome


class MicroscopeImageData(object):

    '''
    Abstract base class for reading image data and metadata from heterogeneous
    file formats using `Bio-Formats <http://www.openmicroscopy.org/site/products/bio-formats>`_
    and the `Open Microscopy Environment (OME) schema <http://www.openmicroscopy.org/Schemas/Documentation/Generated/OME-2015-01/ome.html>`_.

    Individual pixel arrays can be extracted from image files and written to
    PNG files (one single-channel, single-timepoint image per file).
    The corresponding extracted metadata are written to a separate JSON file.
    '''

    __metaclass__ = ABCMeta

    supported_image_formats = {'.tiff', '.tif', '.stk'}  # TODO
    image_file_format = \
        '{experiment}_{cycle:0>2}_s{site:0>4}_C{channel:0>2}{suffix}'

    def __init__(self, upload_folder, experiment_dir, cfg, subexperiment=''):
        '''
        Initialize an instance of class MicroscopeImageData.

        Parameters
        ----------
        upload_folder: str
            absolute path to directory where image (and optionally metadata)
            files were uploaded to
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
        self.upload_folder = upload_folder
        self.experiment_dir = experiment_dir

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
    def image_files(self):
        '''
        Returns
        -------
        List[str]
            names of image files

        Raises
        ------
        OSError
            when no image files are found
        '''
        files = [f for f in os.listdir(self.upload_folder)
                 if os.path.splitext(f)[1]
                 in MicroscopeImageData.supported_image_formats]
        if len(files) == 0:
            raise OSError('No image files found.')
        self._image_files = files
        return self._image_files

    @property
    def metadata_output_dir(self):
        '''
        Returns
        -------
        str
            absolute path to the directory, where extracted metadata should be
            stored
        '''
        self._metadata_output_dir = self.cfg['METADATA_FOLDER_FORMAT'].format(
                                        experiment_dir=self.experiment_dir,
                                        subexperiment=self.subexperiment,
                                        sep=os.path.sep)
        return self._metadata_output_dir

    @property
    def image_output_dir(self):
        '''
        Returns
        -------
        str
            absolute path to the directory, where extracted images should be
            stored
        '''
        self._image_output_dir = self.cfg['IMAGE_FOLDER_FORMAT'].format(
                                        experiment_dir=self.experiment_dir,
                                        subexperiment=self.subexperiment,
                                        sep=os.path.sep)
        return self._image_output_dir

    @property
    def ome_xml_files(self):
        '''
        Returns
        -------
        List[str]
            names of the XML files that contain the extracted OME-XML data
        '''
        self._ome_xml_files = list()
        for f in self.image_files:
            filename = re.sub(r'\.(\w+)$', 'xml', f)
            self._ome_xml_files.append(filename)
        return self._ome_xml_files

    def extract_metadata_from_image_files(self):
        '''
        Extract OME-XML metadata from image files using the
        `Bio-Formats command line tools <http://www.openmicroscopy.org/site/support/bio-formats5.1/users/comlinetools/display.html>`_.
        and save it the data in separate XML files.
        '''
        # TODO: GC3Pie job
        self.ome_xml_image_metadata = dict()
        for i, f in enumerate(self.image_files):
            # Extract OME-XML data from image file
            command = [
                'showinf', '-omexml-only', '-nopix', '-no-upgrade', f
            ]
            process = subprocess.Popen(command,
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE)
            (ome_xml_data, stderrdata) = process.communicate()
            if stderrdata or process.returncode > 0:
                raise subprocess.CalledProcessError('Metadata extraction failed')
            # Write OME-XML data to XML file
            xml_filename = os.path.join(self.metadata_output_dir,
                                        self.ome_xml_files[i])
            with open(xml_filename, 'w') as output_file:
                output_file.write(ome_xml_data)

    def read_image_metadata(self):
        '''
        Read the OME-XML metadata extracted from the image files.

        Returns
        -------
        Dict[str, bioformats.omexml.OMEXML]
            metadata retrieved from image files

        See also
        --------
        `metadata_reader.BioformatsMetadataReader`_
        '''
        self.ome_image_metadata = dict()
        with BioformatsMetadataReader() as reader:
            for f in self._ome_xml_files:
                f_path = os.path.join(self.upload_folder, f)
                self.ome_image_metadata[f] = reader.read(f_path)
        return self.ome_image_metadata

    @staticmethod
    def format_image_metadata(ome_image_metadata):
        '''
        An image file may contain more than one image (pixels) element.
        Planes represent image dimensions other than x/y, such as channels
        or z-stacks acquired at the same microscope stage position.
        Ultimately, we would like to create image files that contain only
        a single-channel image per file. To this end, we group planes per
        channel. In the simplest case, there is only one plane representing
        a single 2D channel image at one z resolution. If there are images at
        multiple z resolutions, they will be grouped together and later on
        projected to 2D.

        Parameters
        ----------
        ome_image_metadata: Dict[str, bioformats.omexml.OMEXML]
            OME metadata retrieved from image files

        Returns
        -------
        List[ChannelMetadata]
            restructured metadata in custom format

        See also
        --------
        `metadata.ChannelMetadata`_
        '''
        restructured_metadata = list()
        for f in ome_image_metadata.keys():
            n_series = ome_image_metadata[f].image_count
            for i in xrange(n_series):
                md = ChannelMetadata()
                md.filename = f

                image = ome_image_metadata[f].image(i)
                md.name = image.Name

                pixels = image.Pixels
                md.dtype = pixels.PixelType
                md.dimensions = (pixels.SizeY, pixels.SizeX)

                n_zstacks = pixels.SizeZ
                n_channels = pixels.SizeC
                n_timepoints = pixels.SizeT
                if n_timepoints > 1:
                    raise NotImplementedError('Only images with a single time '
                                              'point are supported for now.')

                n_planes = pixels.plane_count
                if n_planes > 0 or n_channels > 1 or n_zstacks > 1:
                    # We are dealing with a multi-plane image
                    if n_planes == 0:
                        # Sometimes an image doesn't have any planes, but still
                        # contains multiple channels and/or z-stacks.
                        # For consistency, let's create new plane elements.
                        pixels = ome.create_channel_planes(pixels)

                    plane = pixels.Plane(0)
                    md.position = (plane.PositionY, plane.PositionX)

                    n_planes = pixels.plane_count
                    for c in xrange(n_channels):
                        planes = [pixels.Plane(p) for p in xrange(n_planes)
                                  if c == pixels.Plane(p).TheC]
                        md.channel = c
                        md.channel_name = pixels.Channel(c).Name
                        md.channel_planes = list()
                        for p in planes:
                            md.channel_planes.append(p)
                        restructured_metadata.append(md)
                else:
                    # We are dealing with a single-plane, single-channel image:
                    md.position = None
                    md.channel = None
                    md.channel_name = pixels.Channel(0).Name
                    md.channel_planes = [pixels]
                    restructured_metadata.append(md)

        return restructured_metadata

    @staticmethod
    def format_plate_metadata(ome_plate_metadata):
        '''
        Images may be part of a well plate. The OME schema doesn't provide
        well-specific information at the level of individual images, but makes
        use of a separate "Plate" element, instead. The corresponding metadata
        is generally stored in an additional metadata file.

        Parameters
        ----------
        ome_plate_metadata: Dict[str, bioformats.omexml.OMEXML]
            OME metadata retrieved from additional metadata files

        Returns
        -------
        List[Dict[str, str or int or tuple]]
            restructured metadata in custom format
        '''
        restructured_metadata = list()
        for f in ome_plate_metadata.keys():
            print f

    def determine_missing_image_metadata(self):
        '''
        Determine, which of the required metadata information is not available.

        Returns
        -------
        List[str]
            names of missing information
        '''
        # List comprehension to the max :)
        # Provides the index and the name of the missing information
        missing = [(i, k) for i, md in enumerate(self.image_metadata)
                   for k, v in md.iteritems()
                   if k in ChannelMetadata.required_metadata and v is None]
        self.missing_metadata = missing
        return self.missing_metadata

    @abstractproperty
    def additional_files(self):
        '''
        Returns
        -------
        List[str]
            names of additional microscope specific metadata files
        '''
        pass

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

    @abstractmethod
    def extract_relevant_additional_metadata(self):
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

    def determine_image_positions(self):
        '''
        Determine the position of each image acquisition site relative to its
        corresponding acquisition grid (slide or well in a plate).
        To this end, calculate the relative positions (coordinates) of images
        within each acquisition grid based on the absolute stage positions.

        Raises
        ------
        NotImplementedError
            when wrong well plate formats are supported

        See also
        --------
        `illuminati.stitch`_
        '''
        # Retrieve the stage positions and corresponding filenames
        # for each pixel array.
        position_info = list()
        if self.metadata.values()[0][0]['well']:
            wells = list(set([md[0]['well'] for md in self.metadata.values()]))
            for w in wells:
                positions = [md[i]['position']
                             for i, x in enumerate(xrange(len(md)))
                             for md in self.metadata.values()
                             if md[i]['well'] == w]
                files = [f for i, x in enumerate(xrange(len(md)))
                         for f, md in self.metadata.iteritems()
                         if md[i]['well'] == w]
                position_info.append(dict(zip(files, positions)))
        else:
            positions = [md[i]['position']
                         for i, x in enumerate(xrange(len(md)))
                         for md in self.metadata.values()]
            files = [f for x in xrange(len(md))
                     for f, md in self.metadata.iteritems()]
            position_info.append(dict(zip(files, positions)))

        for p_info in position_info:
            files, positions = p_info.keys(), p_info.values()
            # Calculate the relative coordinates for each unique pair
            # of stage positions.
            unique_positions = list(set(positions))
            index = [unique_positions.index(p) for p in positions]
            unique_coords = stitch.calc_image_coordinates(unique_positions)
            # Map the unique coordinates back.
            coordinates = [unique_coords[i] for i in index]
            for i, f in enumerate(files):
                self.metadata[f][0]['coordinates'] = coordinates[i]

    def extract_image_and_metadata(self, output_dir):
        '''
        Read the actual image data from the input files and write each plane
        into a separate PNG file. Store and the corresponding metadata into a
        JSON file.

        Parameters
        ----------
        output_dir: str
            path to the directory where output image and metadata files should
            be stored
        '''
        self.determine_image_positions()
        metadata_per_plane = dict()
        with BioformatsImageReader() as reader:
            for i, f in enumerate(self.image_files):
                for j, md in enumerate(self.metadata[f]):
                    for c, plane in md['planes'].iteritems():
                        # Perform maximum intensity projection to reduce
                        # dimensionality to 2D if there is more than 1 z-stack
                        stack = np.empty((md['dimensions'][0],
                                          md['dimensions'][1], len(plane)),
                                         dtype=md['type'])
                        for z, p in enumerate(plane):
                            f_path = os.path.join(self.upload_folder, f)
                            stack[:, :, z] = reader.read_image(f_path,
                                                               index=p,
                                                               series=j,
                                                               rescale=False)
                        plane_pixels = np.max(stack, axis=2)
                        # Write plane (2D single-channel image) to file
                        output_image_file = MicroscopeImageData.image_file_format.format(
                                                experiment=self.experiment,
                                                cycle=1,
                                                site=md['site'],
                                                channel=md['channels'][c],
                                                suffix='.png')
                        output_path = os.path.join(output_dir,
                                                   output_image_file)
                        imageutils.save_image(plane_pixels, output_path)
                        # Collect metadata for each plane
                        metadata_per_plane[output_image_file] = {
                                                'cycle': 1,
                                                'site': md['site'],
                                                'row': md['coordinates'][0],
                                                'column': md['coordinates'][1],
                                                'channel': md['channels'][c],
                        }
                        if md['well']:
                            metadata_per_plane[output_image_file].update({
                                                'well': md['well'],
                            })
        # Write collected metadata to file
        output_metadata_file = os.path.join(output_dir,
                                            '%s.metadata' % self.experiment)
        utils.write_json(output_metadata_file, metadata_per_plane)


class BioformatsImageData(MicroscopeImageData):

    def __init__(self, upload_folder, experiment_dir):
        super(BioformatsImageData, self).__init__(upload_folder, experiment_dir)
        self.upload_folder = upload_folder
        self.experiment_dir = experiment_dir

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
        self.additional_metadata = bf.OMEXML()
        return self.additional_metadata


class YokogawaImageData(MicroscopeImageData):

    metadata_formats = {'.mlf', '.mrf'}

    def __init__(self, upload_folder, experiment_dir):
        super(YokogawaImageData, self).__init__(upload_folder, experiment_dir)
        self.upload_folder = upload_folder
        self.experiment_dir = experiment_dir

    @property
    def additional_files(self):
        '''
        Returns
        -------
        Dict[str, str] or None
            names of Yokogawa metadata files

        Raises
        ------
        OSError
            when no or an incorrect number of metadata files are found
        '''
        files = [f for f in os.listdir(self.upload_folder)
                 if os.path.splitext(f)[1]
                 in YokogawaImageData.metadata_formats]
        if len(files) == 0:
            raise OSError('No metadata files found.')
        elif (len(files) > len(YokogawaImageData.metadata_formats)
                or (len(files) < len(YokogawaImageData.metadata_formats)
                    and len(files) > 0)):
            raise OSError('%d metadata files are required: "%s"'
                          % (len(YokogawaImageData.metadata_formats),
                             '", "'.join(YokogawaImageData.metadata_formats)))
        else:
            self._additional_files = dict()
            for md in YokogawaImageData.metadata_formats:
                self._additional_files[md] = [f for f in files
                                              if f.endswith(md)]
        return self._additional_files

    def read_additional_metadata(self):
        '''
        Returns
        -------
        bioformats.omexml.OMEXML
            metadata retrieved from Yokogawa microscope specific files

        See also
        --------
        `metadata_reader.YokogawaMetadataReader`_
        '''
        with YokogawaMetadataReader() as reader:
            mlf_path = os.path.join(self.upload_folder,
                                    self.additional_files['mlf'])
            mrf_path = os.path.join(self.upload_folder,
                                    self.additional_files['mrf'])
            self.additional_metadata = reader.read(mlf_path, mrf_path)
        return self.additional_metadata

    def extract_relevant_additional_metadata(self):
        pass


class VisitronImageData(MicroscopeImageData):

    metadata_formats = {'.nd'}

    def __init__(self, upload_folder, experiment_dir):
        super(VisitronImageData, self).__init__(upload_folder, experiment_dir)
        self.upload_folder = upload_folder
        self.experiment_dir = experiment_dir

    @property
    def additional_files(self):
        '''
        Returns
        -------
        Dict[str, str] or None
            names of Visitron metadata files

        Raises
        ------
        OSError
            when no or an incorrect number of metadata files are found
        '''
        files = [f for f in os.listdir(self.upload_folder)
                 if os.path.splitext(f)[1]
                 in VisitronImageData.metadata_formats]
        if len(files) == 0:
            raise OSError('No metadata files found.')
        elif (len(files) > len(VisitronImageData.metadata_formats)
                or (len(files) < len(VisitronImageData.metadata_formats)
                    and len(files) > 0)):
            raise OSError('%d metadata files are required: "%s"'
                          % (len(VisitronImageData.metadata_formats),
                             '", "'.join(VisitronImageData.metadata_formats)))
        else:
            self._additional_files = dict()
            for md in VisitronImageData.metadata_formats:
                self._additional_files[md] = [f for f in files
                                              if f.endswith(md)]
        return self._additional_files

    def read_additional_metadata(self):
        '''
        Returns
        -------
        bioformats.omexml.OMEXML
            metadata retrieved from Visitron microscope specific files

        See also
        --------
        `metadata_reader.VisitronMetadataReader`_
        '''
        with VisitronMetadataReader() as reader:
            nd_path = os.path.join(self.upload_folder,
                                   self.additional_metadata_files['nd'])
            self.ome_additional_metadata = reader.read(nd_path)
        return self.ome_additional_metadata

    def extract_relevant_additional_metadata(self):
        pass
