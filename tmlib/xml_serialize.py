from lxml import etree
from lxml import objectify
from tmlib.metadata import ChannelImageMetadata
from tmlib.readers import ImageMetadataReader

with ImageMetadataReader() as reader:
    metadata = reader.read('/Users/mdh/testdata/150820-Testset-CV'
                           '/150820-Testset-CV-1/metadata/images.metadata')


obj = ChannelImageMetadata(metadata[0])

element = objectify.Element(obj.__class__.__name__)
for a in dir(obj):
    if a in ChannelImageMetadata.persistent:
        setattr(element, a, getattr(obj, a))

xml_string = etree.tostring(element, pretty_print=True)

recovered_element = objectify.fromstring(xml_string)

recovered_obj = ChannelImageMetadata()
for el in recovered_element.iterchildren():
    setattr(recovered_obj, el.tag, el)
