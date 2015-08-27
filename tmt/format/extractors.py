import os
import re
import glob
import shutil
import lxml
import lxml.html
import lxml.etree
from cached_property import cached_property
from ..utils import write_json
from ..utils import read_json
from ..utils import flatten
from ..cluster import Cluster


class OmeXmlExtractor(Cluster):

    '''
    Class for extraction of metadata from microscopic image files using the
    Bio-Formats command line tool
    `showinf <http://www.openmicroscopy.org/site/support/bio-formats5.1/users/comlinetools/display.html>`_.

    Upon extraction the metadata is formatted according to the
    `Open Microscopy Environment (OME) schema <http://www.openmicroscopy.org/Schemas/Documentation/Generated/OME-2015-01/ome.html>`_
    and written to file as XML.
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
            configuration of GC3Pie logger; either "debug" or "critical"
            (defaults to ``"critical"``)

        Note
        ----
        `output_dir` will be created if it doesn't exist.

        See also
        --------
        `tmt.config`_
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
                    'inputs': input_files[i], 'outputs': output_files[i]}
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
        input_filename = batch['inputs']
        command = [
            'showinf', '-omexml-only', '-nopix', '-novalid', '-no-upgrade',
            input_filename
        ]
        return command

    def collect_extracted_metadata(self):
        '''
        The *showinf* command prints the OME-XML string to standard output.
        GC3Pie redirects the standard output to a log file. Here we copy the
        content of the log file to the files specified by `ome_xml_files`.
        '''
        output_files = glob.glob(os.path.join(self.log_dir, '*.out'))
        for i, f in enumerate(output_files):
            shutil.copyfile(f, os.path.join(self.output_dir,
                                            self.ome_xml_files[i]))


class ImageExtractor(Cluster):

    def __init__(self, input_dir, output_dir, logging_level='critical'):
        '''
        Initialize an instance of class ImageExtractor.

        Parameters
        ----------
        input_dir: str
            absolute path to the directory that contains the image files,
            from which individual images should be extracted (converted)
        output_dir: str
            absolute path to the directory where files containing the extracted
            images should be stored
        logging_level: str, optional
            configuration of GC3Pie logger; either "debug" or "critical"
            (defaults to ``"critical"``)

        Note
        ----
        `output_dir` will be created if it doesn't exist.

        See also
        --------
        `tmt.config`_
        '''
        super(ImageExtractor, self).__init__(logging_level)
        self.input_dir = input_dir
        self.output_dir = output_dir
        if not os.path.exists(self.output_dir):
            os.mkdir(self.output_dir)

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
        # TODO:
        input_filename = batch['inputs']
        output_filename = batch['ouputs']
        s = batch['series']
        p = batch['planes']

        command = [
            'bfconvert', '-series', s, input_filename, output_filename
        ]
        return command

# TODO: make class

def extract_supported_formats(input_filename, output_filename,
                              support_level=0):
    '''
    Extract names and extensions of supported formats from XML or HTML file.

    The XML file can be generated via the Bio-Formats command line tool
    `formatlist <http://www.openmicroscopy.org/site/support/bio-formats5.1/users/comlinetools/formatlist.html>`_::

        formatlist -xml > supported-formats.xml

    The HTML file can be downloaded from the Bio-Formats website, which lists
    `supported formats <http://www.openmicroscopy.org/site/support/bio-formats5.1/supported-formats.html>`_
    together with the level of support for each format::

        wget http://www.openmicroscopy.org/site/support/bio-formats5.1/supported-formats.html

    Parameters
    ----------
    input_filename: str
        absolute path to the XML or HTML file, that specifies the supported
        formats
    output_filename: str
        absolute path to the JSON file, where the extracted data should be
        written in
    support_level: uint, optional
        minimum level of support for reading pixel and metadata,
        where 0 is no support, 1 is "poor" and 5 is "outstanding" support
        (support information is only available for the HTML file)

    Raises
    ------
    OSError
        when `filename` does not exist
    '''
    if not os.path.exists(input_filename):
        raise OSError('File does not exist: %s' % input_filename)

    if input_filename.endswith('xml'):
        tree = lxml.etree.parse(input_filename)
        format_elements = tree.xpath('.//format')
        extensions = list()
        names = list()
        for fe in format_elements:
            names.append(fe.attrib['name'])
            children_elements = fe.getchildren()
            if children_elements:
                ext = [c.attrib['value'] for c in children_elements
                       if c.attrib['name'] == 'extensions'
                       and c.attrib['value']]
                if ext:
                    ext = ext[0].split('|')
                    ext = ['.%s' % e for e in ext]
                    extensions.append(ext)

    elif input_filename.endswith('html'):
        tree = lxml.html.parse(input_filename)
        method_elements = tree.xpath('.//table/thead/tr/th/img/@alt')
        methods = [re.search(r'header-(\w+).png', me).group(1)
                   for me in method_elements]
        pixel_index = methods.index('pixels')
        metadata_index = methods.index('metadata')
        format_elements = tree.xpath('.//div[@id="supported-formats"]/table/tbody/tr')
        extensions = list()
        names = list()
        for fe in format_elements:
            support_level_elements = fe.xpath('td/img/@alt')
            support_level = [int(re.search(r'^(\d)', sle).group(1))
                             if re.search(r'^(\d)', sle) else 0
                             for sle in support_level_elements]
            name_elements = fe.xpath('td/a/em/text()')
            pixel_support = support_level[pixel_index]
            metadata_support = support_level[metadata_index]
            if pixel_support >= 3 and metadata_support >= 3:
                extensions_element = fe.xpath('td/text()')
                if extensions_element:
                    if len(extensions_element[0]) > 1:
                        extensions.append(extensions_element[0].split(', '))
                        names.append(name_elements[0])

    write_json(output_filename, dict(zip(names, extensions)))
