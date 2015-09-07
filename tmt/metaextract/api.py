import os
import re
import glob
import shutil
from cached_property import cached_property
from ..formats import Formats
from ..cluster import ClusterRoutine


class MetadataExtractor(ClusterRoutine):

    '''
    Class for extraction of metadata from microscopic image files using the
    Bio-Formats command line tool
    `showinf <http://www.openmicroscopy.org/site/support/bio-formats5.1/users/comlinetools/display.html>`_.

    Upon extraction, the metadata is formatted according to the
    `Open Microscopy Environment (OME) schema <http://www.openmicroscopy.org/Schemas/Documentation/Generated/OME-2015-01/ome.html>`_
    and written to XML files.
    '''

    def __init__(self, cycle, prog_name, logging_level='critical'):
        '''
        Initialize an instance of class MetadataExtractor.

        Parameters
        ----------
        cycle: Cycle
            cycle object that holds information about the content of the cycle
            directory
        prog_name: str
            name of the corresponding command line interface
        logging_level: str, optional
            configuration of GC3Pie logger; either "debug", "info", "warning",
            "error" or "critical" (defaults to ``"critical"``)

        See also
        --------
        `tmt.cfg`_
        '''
        super(MetadataExtractor, self).__init__(prog_name, logging_level)
        self.cycle = cycle
        if not os.path.exists(self.cycle.ome_xml_dir):
            os.mkdir(self.cycle.ome_xml_dir)
        self.prog_name = prog_name

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
        files = [f for f in os.listdir(self.cycle.image_upload_dir)
                 if os.path.splitext(f)[1] in Formats().supported_extensions]
        if len(files) == 0:
            raise OSError('No image files founds in folder: %s'
                          % self.cycle.image_upload_dir)
        self._image_files = files
        return self._image_files

    @property
    def ome_xml_files(self):
        '''
        Returns
        -------
        List[str]
            names of the XML files that contain the extracted OME-XML data
            (same basename as the image file, but with *.ome.xml* extension)
        '''
        self._ome_xml_files = list()
        for f in self.image_files:
            filename = re.sub(r'\.\w+$', '.ome.xml', f)
            self._ome_xml_files.append(filename)
        return self._ome_xml_files

    def create_joblist(self, **kwargs):
        '''
        Create a list of information required for the creation and processing
        of individual jobs.

        Parameters
        ----------
        cfg_file: str
            absolute path to custom configuration file
        **kwargs: dict
            empty - no additional arguments
        '''
        input_files = [os.path.join(self.cycle.image_upload_dir, f)
                       for f in self.image_files]
        output_files = [os.path.join(self.cycle.ome_xml_dir, f)
                        for f in self.ome_xml_files]
        joblist = [{
                'id': i+1,
                'inputs': [input_files[i]],
                'outputs': [output_files[i]]
            } for i in xrange(len(input_files))]
        return joblist
        pass

    @property
    def log_dir(self):
        '''
        Returns
        -------
        str
            path to the directory where log files should be stored
        '''
        return os.path.join(self.cycle.ome_xml_dir, '..',
                            'log_%s' % self.prog_name)

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
        input_filename = batch['inputs'][0]
        command = [
            'showinf', '-omexml-only', '-nopix', '-novalid', '-no-upgrade',
            input_filename
        ]
        return command

    def run_job(self, batch):
        '''
        Java job.
        '''
        pass

    def collect_job_output(self, joblist):
        '''
        The *showinf* command prints the OME-XML string to standard output.
        GC3Pie redirects the standard output to a log file. Here we copy the
        content of the log file to the files specified by the `ome_xml_files`
        attribute.

        The extracted metadata is used to create custom metadata, which will be
        subsequently used by TissueMAPS.

        Parameter
        '''
        output_files = glob.glob(os.path.join(self.log_dir, '*.out'))
        for i, f in enumerate(output_files):
            shutil.copyfile(f, os.path.join(self.cycle.ome_xml_dir,
                                            self.ome_xml_files[i]))
