import tmt
from tmt.format.extractors import OmeXmlExtractor
from tmt.format.image_data import OmeImageData

upload_folder = '/Users/mdh/tmlib/testdata/visi/150820-Testset-Visi/image_uploads'
upload_folder2 = '/Users/mdh/tmlib/testdata/visi/150820-Testset-Visi/additional_uploads'
output_folder = '/Users/mdh/tmlib/testdata/visi/150820-Testset-Visi/metadata'
experiment_dir = '/Users/mdh/tmlib/testdata/visi/150820-Testset-Visi'
ome_xml_dir = '/Users/mdh/tmlib/testdata/visi/150820-Testset-Visi/metadata'
cfg = tmt.config

bf = OmeXmlExtractor(upload_folder, output_folder)
joblist = bf.create_joblist()
jobs = bf.create_jobs(joblist)
bf.submit(jobs)

bf = OmeImageData(upload_folder, upload_folder2, ome_xml_dir, experiment_dir, cfg)
