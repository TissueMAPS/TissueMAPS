import os
import glob
from .default import DefaultMetadataHandler
from .cellyoyager import CellvoyagerMetadataHandler
from .metamorph import MetamorphMetadataHandler
from ..cluster import ClusterRoutine
from .. import utils
from ..errors import NotSupportedError
from ..formats import Formats


class MetadataConverter(ClusterRoutine):

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
    separate JSON file based to a custom schema.
    '''

    def __init__(self, cycle, file_format, image_file_format_string,
                 prog_name, logging_level='critical'):
        '''
        Initialize an instance of class MetadataConverter.

        Parameters
        ----------
        cycle: Cycle
            cycle object that holds information about the content of the cycle
            directory
        file_format: str
            name of the microscope file format for which additional files
            are provided, e.g. "metamorph"
        image_file_format_string: str
            format string that specifies how the names of the final image PNG
            files should be formatted
        prog_name: str
            name of the corresponding program (command line interface)
        logging_level: str, optional
            configuration of GC3Pie logger; either "debug", "info", "warning",
            "error" or "critical" (defaults to ``"critical"``)

        Raises
        ------
        NotSupportedError
            when `file_format` is not supported
        '''
        super(MetadataConverter, self).__init__(prog_name, logging_level)
        self.cycle = cycle
        self.file_format = file_format
        if self.file_format:
            if self.file_format not in Formats.support_for_additional_files:
                raise NotSupportedError('Additional metadata files are not '
                                        'supported for the provided format')
        self.image_file_format_string = image_file_format_string
        if not os.path.exists(self.cycle.metadata_dir):
            os.mkdir(self.cycle.metadata_dir)

    def write_metadata_to_file(self, metadata):
        '''
        Write serialized metadata to JSON file.

        Parameters
        ----------
        metadata: List[ChannelImageMetadata]
            complete metadata
        '''
        data = dict()
        for md in metadata:
            data[md.name] = md.serialize()
        filename = os.path.join(self.cycle.metadata_dir,
                                self.cycle.image_metadata_file)
        utils.write_json(filename, data)

    def create_joblist(self, **kwargs):
        '''
        Create a list of information required for the creation and processing
        of individual jobs.

        Parameters
        ----------
        **kwargs: dict
            empty - no additional arguments
        '''
        joblist = [{
            'id': 1,
            'inputs': {
                'uploaded_image_files':
                    glob.glob(os.path.join(self.cycle.image_upload_dir, '*')),
                'uploaded_additional_files':
                    glob.glob(os.path.join(self.cycle.additional_upload_dir, '*')),
                'ome_xml_files':
                    glob.glob(os.path.join(self.cycle.ome_xml_dir, '*'))
            },
            'outputs': {
                'metadata_file':
                    os.path.join(self.cycle.metadata_dir,
                                 self.cycle.image_metadata_file)
            }
        }]
        return joblist

    def run_job(self, batch):
        '''
        Format the OMEXML metadata extracted from image files, complement it
        with metadata retrieved from additional files and/or user input
        and write the formatted metadata to a JSON file.
        '''
        if self.file_format == 'metamorph':
            handler = MetamorphMetadataHandler(
                            self.cycle.image_upload_dir,
                            self.cycle.additional_upload_dir,
                            self.cycle.ome_xml_dir,
                            self.cycle.name)
        elif self.file_format == 'cellvoyager':
            handler = CellvoyagerMetadataHandler(
                            self.cycle.image_upload_dir,
                            self.cycle.additional_upload_dir,
                            self.cycle.ome_xml_dir,
                            self.cycle.name)
        else:
            handler = DefaultMetadataHandler(
                            self.cycle.image_upload_dir,
                            self.cycle.additional_upload_dir,
                            self.cycle.ome_xml_dir,
                            self.cycle.name)
        meta = handler.format_image_metadata()
        meta = handler.add_additional_metadata(meta)
        # TODO: how shall we deal with user input?
        meta = handler.determine_grid_coordinates(meta)
        meta = handler.build_filenames_for_extracted_images(
                    meta, self.image_file_format_string)
        self.write_metadata_to_file(meta)

    @property
    def log_dir(self):
        '''
        Returns
        -------
        str
            path to the directory where log files should be stored
        '''
        return os.path.join(self.cycle.cycle_dir, 'log_%s' % self.prog_name)

    def build_command(self, batch):
        '''
        Build a command for GC3Pie submission. For further information on
        the structure of the command see
        `subprocess <https://docs.python.org/2/library/subprocess.html>`_.

        Parameter
        ---------
        batch: Dict[str, int or List[str]]
            id and specification of input/output of the job that should be
            processed

        Returns
        -------
        List[str]
            substrings of the command call
        '''
        job_id = batch['id']
        command = ['metaconvert']
        if self.file_format:
            command += ['-f', self.file_format]
        command += ['run', '-j', str(job_id), self.cycle.cycle_dir]
        return command

    def collect_job_output(self, joblist, **kwargs):
        pass

    def apply_statistics(self, joblist, wells, sites, channels, output_dir,
                         **kwargs):
        pass
