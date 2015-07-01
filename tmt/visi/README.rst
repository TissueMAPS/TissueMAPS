Command line interface
----------------------

Convert `STK <https://www.openmicroscopy.org/site/support/bio-formats5.1/formats/metamorph-stack-stk.html>`_ files acquired with `Visiview <http://www.visitron.de/Products/Software/VisiView/visiview.html>`_ or `Metamorph <http://www.moleculardevices.com/systems/metamorph-research-imaging/metamorph-microscopy-automation-and-image-analysis-software>`_ software into **PNG** images with optional file renaming and intensity projection.

For help, do

.. code::

    visi -h


Positional arguments:

- **run**: run stk to png conversion
- **joblist**: create a joblist YAML file for parallel processing
- **submit**: submit jobs for parallel conversion

Unpacking
---------

The *.png* image files will be written into a sibling folder of the input "STK" folder. The name of the output folder will be determined form the `configuration-settings`_. 


If your input folder contains several *.nd* files, i.e. images from several sub-experiments, you might want to store the resulting *.png* images in separate folders. To this end, use the ``-s`` or ``--split_output`` argument

.. code::

    visi run -s [stk_folder]

This will create separate folders in the output directory using the basename of each corresponding *.nd* file as folder name. Each of these folders will themselves contain a sub-folder with the actual images.

Renaming
--------

You can rename the *.stk* files to encode certain information in the filename string.

If you want to rename files, use the ``-r`` or ``--rename`` argument

.. code::
    
    visi run -r [stk_folder]

By default, images are renamed according to standard visi-specific configuration settings in YAML format:

.. literalinclude:: visi.config
    :language: yaml


If you want to rename files differently, you can use a custom config file. To this end, simply create a copy of the `visi.config` file in your project folder and modify it to your needs.

To use a custom config file and overwrite the default configuration settings, use the ``--visi_config`` argument

.. code::

    visi run -r --visi_config [config_filename] [stk_folder]

..  

    NOTE: TissueMAPS requires the positional information "row" and "column" to be encoded in the filename!


Intensity projection
--------------------

Maximum intensity projection (MIP) is performed by default. If you want to create individual *.png* images for each z-stack use the ``-z`` or ``--zstacks`` argument

.. code::

    visi run -z [stk_folder]
