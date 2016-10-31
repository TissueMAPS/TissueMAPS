# TmLibrary - TissueMAPS library for distibuted image analysis routines.
# Copyright (C) 2016  Markus D. Herrmann, University of Zurich and Robin Hafen
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
import os
import re
import lxml
import lxml.html
import lxml.etree
from cached_property import cached_property
from .utils import flatten
from .readers import JsonReader
from .writers import JsonWriter


class Formats(object):

    '''
    Class for providing information on supported file formats.

    `TissueMAPS` supports most file formats supported by Bio-Formats.
    '''

    #: Some file formats require additional metadata files, which are not
    #: directly supported by Bio-Formats.
    #: For more information, please refer to
    #: :meth:`tmlib.metaconfig.default.configure_ome_metadata_from_additional_files`
    SUPPORT_FOR_ADDITIONAL_FILES = {'cellvoyager', 'visiview'}

    @property
    def _filename(self):
        location = os.path.dirname(os.path.abspath(__file__))
        self.__filename = os.path.join(location, 'formats',
                                       'supported-formats.json')
        return self.__filename

    @cached_property
    def supported_formats(self):
        '''
        Returns
        -------
        Dict[str, List[str]]
            names and file extensions of supported formats as key-value pairs
        '''
        with JsonReader(self._filename) as f:
            supported_formats = f.read()
        supported_formats.update({u'Visiview': [u'.tiff']})
        supported_formats.update({u'Visiview (STK)': [u'.stk', u'.nd']})
        return supported_formats

    @property
    def supported_extensions(self):
        '''
        Returns
        -------
        Set[str]
            file extensions of supported formats
        '''
        all_extensions = flatten(self.supported_formats.values())
        return set(all_extensions)

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

        with JsonWriter() as writer:
            writer.write(self.filename, dict(zip(names, extensions)))
