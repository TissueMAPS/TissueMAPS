Introduction
============

**tmt** is a Python package that bundles image processing tools used by `TissueMAPS <https:{sep}{sep}github.com{sep}HackerMD{sep}TissueMAPS{sep}>`_.

It uses the configuration file ``tmt.config`` to set the experiment layout, such as the directory structure on disk in order to define paths and filenames.


Configuration settings
----------------------

Configurations are defined in YAML format in combination with Python format strings. They are used for the initialization of Python classes, which provide methods for formatting these strings and replace keywords with experiment specific variables. Thereby, you can

You can describe your experiment layout using the following keywords:

- *experiment_dir*: absolute path to the experiment directory
- *experiment*: name of the experiment folder
- *subexperiment*: name of a subexperiment folder, i.e. a subfolder of the experiment folder
- *sep*: path separator
- *cycle*: number of a subexperiment
- *channel*: number of a channel of intensity images (layers)
- *objects*: name of objects in segmentation images (masks)

.. code-block:: yaml

    # Path format strings
    IMAGE_FOLDER_LOCATION: '{experiment_dir}{sep}{subexperiment}{sep}images'
    SHIFT_FOLDER_LOCATION: '{experiment_dir}{sep}{subexperiment}{sep}shift'
    STATS_FOLDER_LOCATION: '{experiment_dir}{sep}{subexperiment}{sep}stats'
    SEGMENTATION_FOLDER_LOCATION: '{experiment_dir}{sep}{subexperiment}{sep}segmentations'
    LAYERS_FOLDER_LOCATION: '{experiment_dir}{sep}layers'
    DATA_FILE_LOCATION: '{experiment_dir}{sep}data.h5'

    # Filename format strings
    SUBEXPERIMENT_FOLDER_FORMAT: '{experiment}_{cycle:0>2}'
    SUBEXPERIMENT_FILE_FORMAT: '{experiment}_{cycle}'
    STATS_FILE_FORMAT: 'illumstats_channel{channel:0>3}.h5'
    SHIFT_FILE_FORMAT: 'shift_descriptor.json'

    # Regular expression patterns to extract information encoded in filenames
    EXPERIMENT_FROM_FILENAME: '^([^_]+)'
    CYCLE_FROM_FILENAME: '_(\d+)_'
    COORDINATES_FROM_FILENAME: '_r(\d+)_c(\d+)_'
    COORDINATES_IN_FILENAME_ONE_BASED: Yes
    SITE_FROM_FILENAME: '_s(\d+)_'
    CHANNEL_FROM_FILENAME: 'C(\d+)\.png$'
    OBJECT_FROM_FILENAME: '_segmented(\w+).png$'

    # Should Vips image processing library be used?
    USE_VIPS_LIBRARY: Yes  # Required for pyramid creation!

    # Should illumination statistics be calculated on log-transformed images?
    LOG_TRANSFORM_STATS: No

    # Hard-coded in TissueMAPS: Don't change these variables!
    LAYERS_FOLDER_LOCATION: '{experiment_dir}{sep}layers'
    ID_TABLES_FOLDER_LOCATION: '{experiment_dir}{sep}id_tables'
    ID_PYRAMIDS_FOLDER_LOCATION: '{experiment_dir}{sep}id_pyramids'
    DATA_FILE_LOCATION: '{experiment_dir}{sep}data.h5'

.. warning:: The quotation marks are generally not required around strings in YAML syntax, but are necessary here because of the parenthesis in the format strings!
