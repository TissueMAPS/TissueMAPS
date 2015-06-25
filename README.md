# TissueMAPS Toolbox #

[tmt](tmt) is a Python package that bundles image processing tools used by [TissueMAPS](https://github.com/HackerMD/TissueMAPS).

It makes use of a YAML configuration settings file [tmt.config](tmt/tmt.config) (see below) in order to specify the experiment layout, i.e. the directory structure on disk, and thereby define paths and filenames.


## Tools ##

The tmt package contains the following subpackages for different image processing routines:

### [align](tmt/align) ###

A package for aligning images between different acquisition cycles.

### [corilla](tmt/corilla) ###

A package for calculating online statistics on images in order to correct illumination artifacts.

### [dafu](tmt/dafu) ###

A package for fusing data produced by [Jterator](https://github.com/HackerMD/Jterator).

### [illuminati](tmt/illuminati) ###

A package for creating pyramid images.

### [visi](tmt/visi) ###

A package for converting Visitron's STK files to PNG images with optional renaming.

*For more details, please refer to the documentation of the individual tools.*


## Configuration settings ##

Configurations are defined in YAML format using Python format strings. They initialize Python classes, which format the path and filename strings and replace the keywords with experiment specific variables.

You can describe your experiment layout using the following keywords:
- *experiment_dir*: absolute path to the experiment directory
- *experiment*: name of the experiment folder
- *subexperiment*: name of a subexperiment folder, i.e. a subfolder of the experiment folder
- *cycle*: number of a subexperiment
- *channel*: number of a channel of intensity images (layers)
- *objects*: name of objects in segmentation images (masks)

```{yaml}
SUBEXPERIMENTS_EXIST: Yes

# Path format strings
IMAGE_FOLDER_LOCATION: '{experiment_dir}/{subexperiment}/TIFF'
SHIFT_FOLDER_LOCATION: '{experiment_dir}/{subexperiment}/ALIGNCYCLES'
STATS_FOLDER_LOCATION: '{experiment_dir}/{subexperiment}/BATCH'
SEGMENTATION_FOLDER_LOCATION: '{experiment_dir}/{subexperiment}/SEGMENTATION'
LAYERS_FOLDER_LOCATION: '{experiment_dir}/layers'
DATA_FILE_LOCATION: '{experiment_dir}/data.h5'

# Filename format strings
SUBEXPERIMENT_FOLDER_FORMAT: '{experiment}_{cycle:0>2}'
SUBEXPERIMENT_FILE_FORMAT: '{experiment}_{cycle}'
STATS_FILE_FORMAT: 'Measurements_batch_illcor_channel{channel:0>3}_zstack000.mat'
SHIFT_FILE_FORMAT: 'shiftDescriptor.json'

# Regular expression patterns to extract information encoded in filenames
EXPERIMENT_FROM_FILENAME: '^([^_]+)'
CYCLE_FROM_FILENAME: '_(\d+)_'
COORDINATES_FROM_FILENAME: '_r(\d+)_c(\d+)_'
COORDINATES_IN_FILENAME_ONE_BASED: Yes
SITE_FROM_FILENAME: '_s(\d+)_'
CHANNEL_FROM_FILENAME: 'C(\d+)\.png$'
OBJECT_FROM_FILENAME: '_segmented(\w+).png$'
```

> NOTE: The quotation marks are generally not required around strings in YAML syntax, but are necessary here because of the parenthesis in the format strings!
