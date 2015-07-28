Command line interface
----------------------

Create pyramids in `zoomify <http://www.zoomify.com/>`_ format. In addition, it can be used to perform several custom image processing tasks, such as correcting images for illumination artifacts, shifting images for alignment between cycles, and rescaling images for convenient display.

For help, do

.. code::

    $ il -h


Positional arguments:

- **channel**: create "channel" layers
- **mask**: create "mask" layers
- **lut**: create ID lookup tables


Creating channel layers
-----------------------

Illuminati allows you to create pyramid images and apply different pre-processing routines "on-the-fly", without having to save intermediate steps to disk. 

For example, in order to create a channel layer corrected for illumination and thresholded for rescaling, do

.. code::

    $ il channel -n [channel_number] -it [project_dir]


The ``-n`` or ``--channel_nr`` argument is required to select the subset of images belonging to the same channel, in this example all images of channel 1.

The ``-i`` or ``--illum_correct`` argument indicates that images should be  correction for illumination artifacts.

The ``-t`` or ``--thresh`` argument indicates that images should be thresholded for rescaling. By default, the threshold level will be the 99.99th percentile calculated on 10 randomly sampled images. You can overwrite these defaults, by either setting different parameters for the threshold level calculation using the ``--thresh_percent`` and ``--thresh_sample`` arguments or by manually setting the threshold level using the ``--thresh_value`` argument.

If you want to run a custom project, i.e. if your project layout deviates from the default `configuration`_, you can create a custom configuration file and make it available to the program using the ``-c`` or ``--config`` argument

.. code::

    $ il channel -n [channel_number] -it -c [config_filename] [project_dir]


Output directories for the different types of pyramids are dynamically determined from the `configuration`_ settings. However, you can also specify a different output directory using the ``-o`` or ``--output`` argument

.. code::

    $ il channel -n [channel_nr] -it -o [output_dir] [project_dir]


If you want the program to only create the stitched mosaic image (without creating a pyramid) you can use the ``--stitch_only`` argument

.. code::

    $ il channel -n [channel_nr] -it --stitch_only -o [output_dir] [project_dir]


In this case you have to explicitly provide the path to the output directory!


Creating mask layers
--------------------

To create a pyramid image of objects outlines from individual segmentation images, do

.. code::

    $ il mask -n [objects_name] [project_dir]

If you rather want to build a pyramid of the whole objects area use the ``-m`` or ``--mask`` argument with "area"

.. code::

    $ il mask -n [objects_name] -m area [project_dir]


Creating global cell id layer:

This layer is not for direct visualization. It is rather used for "on-the-fly" colorization with the values returned by tools, such as the labels of a classifier. To create such a layer use the ``-g`` or ``--global_ids`` argument

.. code::

    $ il mask -n [objects_name] -m area -g [project_dir]


This creates a 16bit RGB pyramid in PNG format!

.. warning::

    Don't use these pyramids for display in the browser! They will be automatically converted to 8bit, which will result in loss of information.


Creating ID lookup tables
-------------------------

These files are required to identify the ID of an object, when the user clicks on a pixel on the mask belonging to that object. They represent int32 `numpy`arrays and are named after the corresponding segmentation files.


.. code::

    $ il lut -n [objects_name] [project_dir]


Configuration settings
----------------------



