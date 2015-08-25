from abc import ABCMeta
from abc import abstractmethod
import sys
import os
import re
import subprocess
import tempfile
import traceback
import openslide
import bioformats as bf
# import javabridge
from lxml import etree


class MetadataReader(object):

    '''
    Abstract base class for reading metadata from files on disk.
    '''

    __metaclass__ = ABCMeta

    def __enter__(self):
        return self

    @abstractmethod
    def read(self, filename):
        pass

    def __exit__(self, type, value, traceback):
        pass


class BioformatsMetadataReader(MetadataReader):

    def __enter__(self):
        # NOTE: updated "loci_tools.jar" file to latest schema:
        # http://downloads.openmicroscopy.org/bio-formats/5.1.3
        # javabridge.start_vm(class_path=bf.JARS, run_headless=True)
        return self

    def read(self, filename):
        '''
        Read Open Microscopy Environment (OME) metadata from XML file on disk.

        For details on reading metadata via Bio-Format from Python, see
        `OMEXML <http://pythonhosted.org/python-bioformats/#metadata>`_.

        Unfortunately, the documentation is very sparse.
        If you need additional information, refer to the relevant
        `source code <https://github.com/CellProfiler/python-bioformats/blob/master/bioformats/omexml.py>`_.

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
        NotImplementedError
            when the file format is not supported
        '''
        # ome_xml_data = bf.get_omexml_metadata(filename)
        with open(filename, 'r') as f:
            ome_xml_data = f.read()
        metadata = bf.OMEXML(ome_xml_data)
        return metadata

    def __exit__(self, except_type, except_value, except_trace):
        # javabridge.kill_vm()
        # if except_type is javabridge.JavaException:
        #     raise NotImplementedError('File format is not supported.')
        if except_value:
            sys.stdout.write('The following error occurred:\n%s'
                             % str(except_value))
            for tb in traceback.format_tb(except_trace):
                sys.stdout.write(tb)


class OpenslideMetadataReader(MetadataReader):

    def read(self, filename):
        '''
        Read metadata from whole slide images.

        For details on reading metadata via openslide from Python, see
        `online documentation <http://openslide.org/api/python/>`_.

        Parameters
        ----------
        filename: str
            absolute path to the file

        Returns
        -------
        openslide.OpenSlide
            image metadata

        Raises
        ------
        NotImplementedError
            when the file format is not supported
        '''
        metadata = openslide.OpenSlide(filename)
        return metadata

    def __exit__(self, except_type, except_value, except_trace):
        if except_type is openslide.OpenSlideUnsupportedFormatError:
            raise NotImplementedError('File format is not supported.')
        if except_type is openslide.OpenSlideError:
            sys.stdout.write('The following error occurred:\n%s'
                             % str(except_value))
            for tb in traceback.format_tb(except_trace):
                sys.stdout.write(tb)


class YokogawaMetadataReader(MetadataReader):

    '''
    Class for reading metadata from files formats specific for the Yokogawa
    CellVoyager 7000 microscope, which are not supported by Bio-Formats.

    The reader reads the XML files, extracts the relevant data and stores
    them as OME elements according to the Bio-Formats convention.

    Examples
    --------
    >>> mlf_filename = '/path/to/metadata/MeasurementData.mlf'
    >>> mrf_filename = '/path/to/metadata/MeasurementDetail.mrf'
    >>> with CellvoyagerReader() as reader:
    ...     metadata = reader.read(mlf_filename, mrf_filename)
    >>> type(metadata)
    bioformats.omexml.OMEXML
    '''

    def read(self, mlf_filename, mrf_filename):
        '''
        Read metadata from vendor specific files on disk.

        Parameters
        ----------
        mlf_filename: str
            absolute path to the *.mlf* file
        mrf_filename: str
            absolute path to the *.mrf* file

        Returns
        -------
        bioformats.omexml.OMEXML
            image and plate metadata
        '''
        # Unfortunately, we cannot read the required metadata via
        # Bio-Formats directly. To be compatible with the OME schema,
        # we read the XML metadata from the "MeasurementDetail.mrf" and
        # "MeasurmentData.mlf" files manually and store them in an
        # OMEXML object.
        # 1) Obtain the positional information for each image acquisition
        # site from the ".mlf" file:
        mlf_tree = etree.parse(mlf_filename)
        mlf_root = mlf_tree.getroot()
        mlf_elements = mlf_root.xpath('.//bts:MeasurementRecord',
                                      namespaces=mlf_root.nsmap)
        mlf_ns = mlf_root.nsmap['bts']
        # 2) Extract relevant information and store it in an OMEXML object
        metadata = bf.OMEXML()
        metadata.image_count = len(mlf_elements)
        well_info = list()
        for i, e in enumerate(mlf_elements):
            metadata.image(i).Name = e.text
            pixels = metadata.image(i).Pixels
            pixels.SizeT = 1
            pixels.SizeC = 1
            pixels.SizeZ = 1
            pixels.plane_count = 1
            pixels.Plane(0).TheT = 0
            pixels.Plane(0).TheZ = 0
            if e.attrib['{%s}Type' % mlf_ns] == 'IMG':
                pixels.Plane(0).TheC = e.attrib['{%s}Ch' % mlf_ns]
                pixels.Channel(0).Name = e.attrib['{%s}Ch' % mlf_ns]
            else:
                # In case of "ERR" the channel number is not provided
                pixels.Plane(0).TheC = None
                pixels.Channel(0).Name = None
            pixels.Plane(0).PositionX = float(e.attrib['{%s}X' % mlf_ns])
            pixels.Plane(0).PositionY = float(e.attrib['{%s}Y' % mlf_ns])
            # The Bio-Formats OME schema doesn't provide information about
            # wells at the individual image level: see
            # http://www.openmicroscopy.org/Schemas/Documentation/Generated/OME-2015-01/ome.html
            # Instead, it provides a "Plate" element, which contains
            # "Well" elements, which themselves contain "WellSample"
            # elements. A "WellSample" represents an individual image
            # and holds the corresponding metadata.
            # Therefore, we first collect well information for each image
            # and then later create a Plate object, which can hold this
            # information. This requires a lot of recursion to get
            # well information for an individual image.
            # I'm not sure the Bio-Formats compatibility is worth the
            # indexing nightmare at this level, but let's stick to it for
            # now.
            well_info.append({
                'well_site': int(e.attrib['{%s}FieldIndex' % mlf_ns]),
                'well_position': (int(e.attrib['{%s}Row' % mlf_ns]),
                                  int(e.attrib['{%s}Column' % mlf_ns]))
            })

        # 3) Obtain the general experiment information and well plate format
        # specifications from the ".mrf" file and store them in the OMEXML
        # object as well:
        mrf_tree = etree.parse(mrf_filename)
        mrf_root = mrf_tree.getroot()
        mrf_ns = mrf_root.nsmap['bts']
        e = mrf_root
        plate_name = e.attrib['{%s}Title' % mrf_ns]
        plate = metadata.PlatesDucktype(metadata.root_node).newPlate(
                                                        name=plate_name)
        plate.RowNamingConvention = 'number'
        plate.ColumnNamingConvention = 'number'
        plate.Rows = e.attrib['{%s}RowCount' % mrf_ns]
        plate.Columns = e.attrib['{%s}ColumnCount' % mrf_ns]
        wells = [wi['well_position'] for wi in well_info]
        for w in set(wells):
            # Create a "Well" instance for each imaged well in the plate
            well = metadata.WellsDucktype(plate).new(row=w[0], column=w[1])
            samples = metadata.WellSampleDucktype(well.node)
            well_sites = [wi['well_site'] for wi in well_info
                          if wi['well_position'] == w]
            for site in set(well_sites):
                image_indices = [i for i, s in enumerate(well_info)
                                 if s['well_site'] == site
                                 and s['well_position'] == w]
                filenames = [metadata.image(i).Name for i in image_indices]
                i = image_indices[0]
                # Create a "WellSample" instance for each acquisition site
                well_sample_ix = site-1  # zero-based
                samples.new(index=well_sample_ix)
                # Store positional information for each acquisition site
                samples[well_sample_ix].PositionX = \
                    metadata.image(i).Pixels.Plane(0).PositionX
                samples[well_sample_ix].PositionY = \
                    metadata.image(i).Pixels.Plane(0).PositionY
                # Provide the names of the corresponding images
                samples[well_sample_ix].ImageRef = filenames

        return metadata


class VisitronMetadataReader(MetadataReader):

    def read(self, filename):
        pass
