'''
OME-XML declaration configuration.
For details see `OME model <http://www.openmicroscopy.org/site/support/ome-model/>`_
'''

OME_VERSION = '2015-01'

XML_FIELDNAMES = {
    'schema_name': 'http://www.openmicroscopy.org/Schemas/OME/{version}',
    'schema_inst': 'http://www.w3.org/2001/XMLSchema-instance',
    'schema_loc': 'http://www.openmicroscopy.org/Schemas/OME/{version} http://www.openmicroscopy.org/Schemas/OME/{version}/ome.xsd',
    'sa': 'http://www.openmicroscopy.org/Schemas/SA/{version}',
    'spw': 'http://www.openmicroscopy.org/Schemas/SPW/{version}'
}

XML_DECLARATION = '''<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<OME xmlns="{schema_name}" xmlns:xsi="{schema_inst}" xsi:schemaLocation="{schema_loc}">
    <StructuredAnnotations xmlns="{sa}">
    </StructuredAnnotations>
    <SPW xmlns="{spw}">
    </SPW>
</OME>
'''.format(**XML_FIELDNAMES).format(version=OME_VERSION)

# XML_DECLARATION = '''<?xml version="1.0" encoding="UTF-8"?>
# <OME:OME xmlns:ROI="http://www.openmicroscopy.org/Schemas/ROI/2015-01"
#     xmlns:OME="http://www.openmicroscopy.org/Schemas/OME/2015-01"
#     xmlns:BIN="http://www.openmicroscopy.org/Schemas/BinaryFile/2015-01"
#     xmlns:SPW="http://www.openmicroscopy.org/Schemas/SPW/2015-01"
#     xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
#     xsi:schemaLocation="http://www.openmicroscopy.org/Schemas/OME/2015-01
#                         http://www.openmicroscopy.org/Schemas/OME/2015-01/ome.xsd">

#     <SPW:Plate
#         ID="Plate:1"
#         Name="Control Plate"
#         ColumnNamingConvention="letter"
#         RowNamingConvention="number"
#         Columns="12"
#         Rows="8"
#         >
#         <SPW:Description></SPW:Description>

#         <!-- repeat SPW:Well for # of wells in the plate that contain images -->
#         <SPW:Well ID="Well:1" Column="0" Row="0">
#             <!-- repeat SPW:WellSample for # of images taken in the well -->
#             <SPW:WellSample ID="WellSample:1" Index="0">
#                 <!--
#                         if there is an image associated with this SPW:WellSample
#                         it is linked using an SPW:ImageRef
#                     -->
#                 <OME:ImageRef ID="Image:0"/>
#             </SPW:WellSample>
#         </SPW:Well>
#     </SPW:Plate>
#     <!-- plus one more Plate for each Plate in this set -->

#     <!-- SPW:Screen is not required -->

#     <!-- The OME:Image element follows the structure for the OME Compliant File Specification -->
#     <OME:Image ID="Image:0" Name="Series 1">
#         <OME:AcquisitionDate>2008-02-06T13:43:19</OME:AcquisitionDate>
#         <OME:Description>An example OME compliant file, based on Olympus.oib</OME:Description>
#         <OME:Pixels DimensionOrder="XYCZT" ID="Pixels:0"
#             PhysicalSizeX="0.207" PhysicalSizeY="0.207"
#             SizeC="3" SizeT="16" SizeX="1024" SizeY="1024" SizeZ="1"
#             TimeIncrement="120.1302" Type="uint16">
#             <OME:Channel EmissionWavelength="523" ExcitationWavelength="488" ID="Channel:0:0"
#                 IlluminationType="Epifluorescence" Name="CH1" SamplesPerPixel="1"
#                 PinholeSize="103.5" AcquisitionMode="LaserScanningConfocalMicroscopy"/>
#             <OME:Channel EmissionWavelength="578" ExcitationWavelength="561" ID="Channel:0:1"
#                 IlluminationType="Epifluorescence" Name="CH3" SamplesPerPixel="1"
#                 PinholeSize="127.24" AcquisitionMode="LaserScanningConfocalMicroscopy"/>
#             <OME:Channel ExcitationWavelength="488" ID="Channel:0:2"
#                 IlluminationType="Transmitted"
#                 ContrastMethod="DIC" Name="TD1" SamplesPerPixel="1"
#                 AcquisitionMode="LaserScanningConfocalMicroscopy"/>
#             <BIN:BinData BigEndian="false" Length="0"/>
#         </OME:Pixels>
#     </OME:Image>
# </OME:OME>
# '''
