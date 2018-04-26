# Small utility script to generate a folder with all the necessary inputs for the automated tests in TissueMaps v0.2.2
# Written by Joel Luethi
# joel.luethi@uzh.ch

# LIMITATIONS
# The experiment_description is also currently hard coded and would need to be changed manually if its different

import os
import json
from tmclient.api import TmClient
import shutil
import yaml

# Variables to be set before using the script
folderPath="/PATH/TO/TARGET/FOLDER"  # Where all the data for the test case will be saved
host="app.tissuemaps.org"
port = "80"
experimentName="NameOfExperiment"
username="USERNAME"
password="PASSWORD"
folderContainingOriginalImages = ["/PATH/TO/FOLDER/CONTAINING/ORIGINAL/IMAGES"]  # List of all acquisitions
estimatedRuntime = 7200  # In seconds. After that amount, the test will run into a timeout


# Create tmclient instance
client = TmClient(host, port, username, password, experimentName)
# print json.dumps(mapobject_download,sort_keys=True, indent = 4, separators=(',', ': '))

# Write experiment_description file
exp_description = dict(
    microscope_type = "cellvoyager",
    workflow_type = "canonical",
    plate_format = 384,
    plate_acquisition_mode = "basic"
)

with open(os.path.join(folderPath,'experiment_description.yaml'),'w') as outfile:
    yaml.dump(exp_description, outfile, default_flow_style=False, explicit_start=True)

# Get plate name
plateDownload = client.get_plates()
plate_name = plateDownload[0]['name']

# Get acquisition name
acquisitionDownload = client.get_acquisitions()
nbAcquisitions = len(acquisitionDownload)

# Make the folder where the images go
print "Making folder structure"
imageFolderName_0 = os.path.join(folderPath,"plates")
if not os.path.exists(imageFolderName_0):
    os.makedirs(imageFolderName_0)

imageFolderName_1 = os.path.join(imageFolderName_0, plate_name)
if not os.path.exists(imageFolderName_1):
    os.makedirs(imageFolderName_1)

imageFolderName_2 = os.path.join(imageFolderName_1,'acquisitions')
if not os.path.exists(imageFolderName_2):
    os.makedirs(imageFolderName_2)

# Copying all the acquisitions
for i in range(nbAcquisitions):
    acquisition_name = acquisitionDownload[i]['name']
    imageFolderName = os.path.join(imageFolderName_2,acquisition_name)
    if not os.path.exists(imageFolderName):
        os.makedirs(imageFolderName)

    # Copy image files to directory
    src_files = os.listdir(folderContainingOriginalImages[i])
    for file_name in src_files:
        full_file_name = os.path.join(folderContainingOriginalImages[i], file_name)
        if (os.path.isfile(full_file_name)):
            print "Copying " + file_name
            shutil.copy(full_file_name, imageFolderName)

# Make a folder for jterator
jteratorFolderName = os.path.join(folderPath, "jterator")
if not os.path.exists(jteratorFolderName):
    os.makedirs(jteratorFolderName)

# Download jterator pipeline & handles files
print "Downloading Jterator pipeline"
client.download_jterator_project_files(jteratorFolderName)


# Extract the list of mapojects present in the experiment
mapobject_types = list()
mapobject_download = client.get_mapobject_types()

for mapobject in mapobject_download:
    mapobject_types.append(mapobject['name'])

# Get wells information
wellDownload = client.get_wells()

# Get wells information
siteDownload = client.get_sites()

# Get cycle information
channelsDownload = client.get_channels()

well_dimensions = wellDownload[0]['dimensions']
# Write expectation file
expectations = dict(
    n_channels = len(channelsDownload),
    n_mapobject_types = len(mapobject_types),
    n_wells = len(wellDownload),
    well_dimensions = well_dimensions,
    n_sites = len(siteDownload),
    n_cycles = len(acquisitionDownload)
)
with open(os.path.join(folderPath,'expectations.yaml'),'w') as outfile:
    yaml.dump(expectations, outfile, explicit_start=True)

# Write settings file
settings_dict = dict(
    workflow_timeout = estimatedRuntime
)

with open(os.path.join(folderPath,'settings.yaml'),'w') as outfile:
    yaml.dump(settings_dict, outfile, default_flow_style=False, explicit_start=True)


# Download feature values and metadata for all mapobject types
for mapobject_type in mapobject_types:
    print 'Downloading ' + mapobject_type
    fileNameFeatures = os.path.join(folderPath, 'feature-values_' + mapobject_type + '.csv')
    fileNameMetadata = os.path.join(folderPath, 'metadata_' + mapobject_type + '.csv')

    feature_values = client.download_feature_values(mapobject_type_name = mapobject_type)
    feature_values.to_csv(fileNameFeatures, index = False)

    metadata = client.download_object_metadata(mapobject_type_name = mapobject_type)
    metadata.to_csv(fileNameMetadata, index=False)

# Download workflow description
workflowFilename = os.path.join(folderPath, 'workflow_description.yaml')
client.download_workflow_description_file(workflowFilename)
