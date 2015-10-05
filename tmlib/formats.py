import os
import re
import lxml
import lxml.html
import lxml.etree
from .utils import flatten
from .readers import SupportedFormatsReader
from .writers import SupportedFormatsWriter


class Formats(object):

    '''
    Class for providing information on file formats supported by Bio-Formats.
    '''

    SUPPORT_FOR_ADDITIONAL_FILES = {'metamorph', 'cellvoyager'}

    @property
    def filename(self):
        '''
        Returns
        -------
        str
            absolute path to the file, where information about supported
            formats is stored
        '''
        location = os.path.dirname(os.path.abspath(__file__))
        self.__json_filename = os.path.join(location, 'formats',
                                            'supported-formats.json')
        return self.__json_filename

    @property
    def supported_formats(self):
        '''
        Returns
        -------
        Dict[str, List[str]]
            names and file extensions of supported formats as key-value pairs
        '''
        with SupportedFormatsReader() as reader:
            self._supported_formats = reader.read(self.filename)
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

    def extract_supported_formats(self, input_filename, support_level=0):
        '''
        Extract names and extensions of supported formats from XML or HTML file
        and save them as key-value pairs in a JSON file.

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
        support_level: uint, optional
            minimum level of support for reading pixel and metadata,
            where 0 is no support, 1 is "poor" and 5 is "outstanding" support
            (Note: support information is only available for the HTML file)

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

        with SupportedFormatsWriter() as writer:
            writer.write(self.filename, dict(zip(names, extensions)))
