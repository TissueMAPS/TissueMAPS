import os
import re
import glob
import shutil
import yaml
from cached_property import cached_property
from ..format import supported_formats
from ..utils import flatten
from ..cluster import ClusterRoutine


class OmeXmlExtractor(ClusterRoutine):

    '''
    Class for extraction of metadata from microscopic image files using the
    Bio-Formats command line tool
    `showinf <http://www.openmicroscopy.org/site/support/bio-formats5.1/users/comlinetools/display.html>`_.

    Upon extraction, the metadata is formatted according to the
    `Open Microscopy Environment (OME) schema <http://www.openmicroscopy.org/Schemas/Documentation/Generated/OME-2015-01/ome.html>`_
    and written to XML files.
    '''

    def __init__(self, input_dir, output_dir, logging_level='critical'):
        '''
        Initialize an instance of class OmeXmlExtractor.

        Parameters
        ----------
        input_dir: str
            absolute path to the directory that contains the images, from which
            metadata should be extracted
        output_dir: str
            absolute path to the directory where files containing the extracted
            metadata should be stored
        logging_level: str, optional
            configuration of GC3Pie logger; either "debug", "info", "warning",
            "error" or "critical" (defaults to ``"critical"``)

        Note
        ----
        `output_dir` will be created if it doesn't exist.

        See also
        --------
        `tmt.cfg`_
        '''
        super(OmeXmlExtractor, self).__init__(logging_level)
        self.input_dir = input_dir
        self.output_dir = output_dir
        if not os.path.exists(self.output_dir):
            os.mkdir(self.output_dir)

    @property
    def name(self):
        '''
        Returns
        -------
        str
            name of the program in lower case letters
        '''
        self._name = self.__class__.__name__.lower()
        return self._name

    def print_supported_formats(self):
        '''
        Print supported file formats to standard output in YAML format.
        '''
        print yaml.dump(supported_formats, default_flow_style=False)

    @property
    def supported_extensions(self):
        '''
        Returns
        -------
        Set[str]
            file extensions of supported formats
        '''
        all_extensions = flatten(supported_formats.values())
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
        files = [f for f in os.listdir(self.input_dir)
                 if os.path.splitext(f)[1] in self.supported_extensions]
        if len(files) == 0:
            raise OSError('No image files founds in folder: %s'
                          % self.input_dir)
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

    def create_joblist(self, batch=None):
        '''
        Create a list of information required for the creation and processing
        of individual jobs.

        Parameters
        ----------
        batch_size: int, optional
            number of files that should be processed together as one job
        '''
        input_files = [os.path.join(self.input_dir, f)
                       for f in self.image_files]
        output_files = [os.path.join(self.output_dir, f)
                        for f in self.ome_xml_files]
        joblist = [{'id': i+1,
                    'input': input_files[i], 'output': output_files[i]}
                   for i in xrange(len(input_files))]
        return joblist

    @property
    def log_dir(self):
        '''
        Returns
        -------
        str
            path to the directory where log files should be stored
        '''
        return os.path.join(self.output_dir, '..', 'log_%s' % self.name)

    def build_command(self, batch=None):
        '''
        Build a command for GC3Pie submission. For further information on
        the structure of the command see
        `subprocess <https://docs.python.org/2/library/subprocess.html>`_.

        Parameter
        ---------
        batch: Dict[str, int or List[str]], optional
            id and specification of input/output of the job that should be
            processed

        Returns
        -------
        List[str]
            substrings of the command call
        '''
        input_filename = batch['input']
        command = [
            'showinf', '-omexml-only', '-nopix', '-novalid', '-no-upgrade',
            input_filename
        ]
        return command

    def run(self, batch):
        pass

    def collect_extracted_metadata(self):
        '''
        The *showinf* command prints the OME-XML string to standard output.
        GC3Pie redirects the standard output to a log file. Here we copy the
        content of the log file to the files specified by the `ome_xml_files`
        attribute.

        The extracted metadata is used to create custom metadata, which will be
        subsequently used by TissueMAPS.
        '''
        output_files = glob.glob(os.path.join(self.log_dir, '*.out'))
        for i, f in enumerate(output_files):
            shutil.copyfile(f, os.path.join(self.output_dir,
                                            self.ome_xml_files[i]))
