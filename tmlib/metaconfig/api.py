import os
import re
import logging
import importlib
from ..cluster import ClusterRoutines
from ..writers import JsonWriter
from ..writers import XmlWriter
from ..errors import NotSupportedError
from ..errors import MetadataError
from ..formats import Formats

logger = logging.getLogger(__name__)


class MetadataConfigurator(ClusterRoutines):

    '''
    Abstract base class for the handling of image metadata.

    It provides methods for conversion of metadata extracted from heterogeneous
    microscope file formats using the
    `Bio-Formats <http://www.openmicroscopy.org/site/products/bio-formats>`_
    library into a custom format. The original metadata has to be available
    in OMEXML format according to the
    `OME schema <http://www.openmicroscopy.org/Schemas/Documentation/Generated/OME-2015-01/ome.html>`_.

    The class further provides methods to complement the automatically
    retrieved metadata by making use of additional microscope-specific metadata
    files and/or user input.

    The metadata corresponding to the final PNG images are stored in a
    separate JSON file.
    '''

    def __init__(self, experiment, prog_name, verbosity):
        '''
        Initialize an instance of class MetadataConfigurator.

        Parameters
        ----------
        experiment: Experiment
            configured experiment object
        prog_name: str
            name of the corresponding program (command line interface)
        verbosity: int
            logging level

        Raises
        ------
        NotSupportedError
            when `file_format` is not supported

        See also
        --------
        `tmlib.cfg`_
        '''
        super(MetadataConfigurator, self).__init__(
                experiment, prog_name, verbosity)
        self.experiment = experiment
        self.prog_name = prog_name
        self.verbosity = verbosity

    @property
    def image_file_format_string(self):
        '''
        Returns
        -------
        image_file_format_string: str
            format string that specifies how the names of the final image PNG
            files should be formatted
        '''
        self._image_file_format_string = self.experiment.cfg.IMAGE_FILE
        return self._image_file_format_string

    def create_job_descriptions(self, **kwargs):
        '''
        Create job descriptions for parallel computing.

        Parameters
        ----------
        **kwargs: dict
            empty - no additional arguments

        Returns
        -------
        Dict[str, List[dict] or dict]
            job descriptions
        '''
        if kwargs['format'] != 'default':
            if kwargs['format'] not in Formats.SUPPORT_FOR_ADDITIONAL_FILES:
                raise NotSupportedError(
                        'The specified format is not supported.\n'
                        'Possible options are: "%s"'.format(
                            '", "'.join(Formats.SUPPORT_FOR_ADDITIONAL_FILES)))
        job_descriptions = dict()
        job_descriptions['run'] = list()
        for i, upload in enumerate(self.experiment.uploads):
            description = {
                'id': i+1,
                'inputs': {
                    'uploaded_image_files': [
                        os.path.join(upload.image_dir, f)
                        for f in upload.image_files
                    ],
                    'uploaded_additional_files': [
                        os.path.join(upload.additional_dir, f)
                        for f in upload.additional_files
                    ],
                    'ome_xml_files': [
                        os.path.join(upload.ome_xml_dir, f)
                        for f in upload.ome_xml_files
                    ]
                },
                'outputs': {
                    'metadata_files': [
                        os.path.join(upload.dir, upload.image_metadata_file)
                    ],
                    'mapper_files': [
                        os.path.join(upload.dir, upload.image_mapper_file)
                    ]
                },
                'z_stacks': kwargs['z_stacks']
            }
            description.update(kwargs)
            job_descriptions['run'].append(description)

        return job_descriptions

    def _handler_factory(self, file_format):
        module_name = re.sub(r'([^.]\w+)$', file_format, __name__)
        logger.debug('import module for specified format "%s"' % module_name)
        module_inst = importlib.import_module(module_name)
        class_name = '%sMetadataHandler' % file_format.capitalize()
        logger.debug('instantiate metadata handler class "%s"' % class_name)
        class_inst = getattr(module_inst, class_name)
        return class_inst

    def run_job(self, batch):
        '''
        Format the OMEXML metadata extracted from image files, complement it
        with metadata retrieved from additional files and/or user input
        and write the formatted metadata to a JSON file.

        The actual processing is done by `MetadataHandler` classes. Some file
        formats require additional customization, either because Bio-Formats
        does not fully support them or because the microscopes provides
        insufficient information in the image files.
        To overcome these limitations, one can create a subclass
        of the `MetaHandler` abstract base class and overwrite methods for 
        customization. Custom handlers already exists for the file formats
        generated by the Yokogawa CellVoyager 7000 microscope ("cellvoyager")
        and Visitron microscopes ("visiview"), for example. The list of custom
        handlers can be further extended by creating a new module in the
        `metaconfig` package with the same name as the file format and adding
        a custom `MetaHandler` subclass to it, whose name has to be pretended
        with the capitalized name of the file format.
        For example, given a file format called "example" one would need to
        create the module "tmlib.metaconfig.example" and it would have to
        contain a class named "ExampleMetadataHandler"
        that inherits from `MetadataHandler` and overwrites the abstract
        methods and potentially others if required.
        The new handler class would then automatically be picked up and used
        when the value of the "format" argument is set to "example".

        See also
        --------
        `tmlib.metaconfig.default`_
        '''
        handler_class = self._handler_factory(batch['format'])
        handler = handler_class(
                            batch['inputs']['uploaded_image_files'],
                            batch['inputs']['uploaded_additional_files'],
                            batch['inputs']['ome_xml_files'],
                            self.experiment.name,
                            self.experiment.dimensions)
        if batch['z_stacks']:
            logger.info('focal planes will be kept')
        else:
            logger.info('focal planes will be projected to a 2D plane')
        handler.configure_ome_metadata_from_image_files()
        # batch['keep_zstacks']
        handler.configure_ome_metadata_from_additional_files()
        missing_md = handler.determine_missing_metadata()
        if missing_md:
            if batch['regex'] or handler.REGEX:
                logger.warning('required metadata information is missing')
                logger.info('try to retrieve missing metadata from filenames '
                            'using regular expression')
                handler.configure_metadata_from_filenames(batch['regex'])
            else:
                raise MetadataError(
                    'The following metadata information is missing:\n"%s"\n'
                    'You can provide a regular expression in order to '
                    'retrieve the missing information from filenames '
                    % '", "'.join(missing_md))
        missing_md = handler.determine_missing_metadata()
        if missing_md:
            raise MetadataError(
                    'The following metadata information is missing:\n"%s"\n'
                    % '", "'.join(missing_md))
        # Once we have collected basic metadata such as information about
        # channels and focal planes, we try to determine the relative position
        # of images within the acquisition grid
        try:
            logger.info('try to determine grid coordinates from microscope '
                        'stage positions')
            handler.determine_grid_coordinates_from_stage_positions()
        except MetadataError as error:
            logger.warning('microscope stage positions are not available: "%s"'
                           % str(error))
            logger.info('try to determine grid coordinates from provided '
                        'stitch layout')
            handler.determine_grid_coordinates_from_layout(
                    stitch_layout=batch['stitch_layout'],
                    stitch_major_axis=batch['stitch_major_axis'],
                    stitch_dimensions=(batch['stitch_vertical'],
                                       batch['stitch_horizontal']))

        handler.update_channel_ids()
        md = handler.update_plane_ids()
        imgmap = handler.create_image_hashmap()
        self._write_metadata_to_file(batch['outputs']['metadata_files'], md)
        self._write_mapper_to_file(batch['outputs']['mapper_files'], imgmap)

    @staticmethod
    def _write_metadata_to_file(filenames, metadata):
        with XmlWriter() as writer:
            f = filenames[0]
            data = metadata.to_xml()
            logger.info('write metadata to file')
            writer.write(f, data)

    @staticmethod
    def _write_mapper_to_file(filenames, hashmap):
        with JsonWriter() as writer:
            f = filenames[0]
            logger.info('write hashmap to file')
            writer.write(f, hashmap)

    def collect_job_output(self, batch):
        raise AttributeError('"%s" object doesn\'t have a "collect_job_output"'
                             ' method' % self.__class__.__name__)

    def apply_statistics(self, job_descriptions, wells, sites, channels, output_dir,
                         **kwargs):
        raise AttributeError('"%s" object doesn\'t have a "apply_statistics"'
                             ' method' % self.__class__.__name__)
