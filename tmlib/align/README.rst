Command line interface
----------------------

Align images of the same sample acquired at different time points (i.e. in different "cycles"), which may be shifted in y, x direction relative to each other (same scale and no rotation!).

For help, do

.. code::
    
    $ align -h


Positional arguments:

- **run**: run shift calculation
- **joblist**: create a joblist YAML file for parallel processing
- **submit**: submit jobs for parallel shift calculation
- **fuse**: fuse calculated shift and overlap values, and create the shift descriptor JSON file
- **apply**: apply calculated shifts and overlaps stored in shift descriptor to images in order to align (i.e. crop) them

.. _image-registration:

Image registration
------------------

The information required for alignment is generated in two steps:

1) **Image registration**: calculate shift of an image relative to a reference image (*run* step)
2) **Overlap calculation**: calculate global overlap of images after shifting (*fuse* step)

You can define which channel ``--ref_channel`` and cycle ``--ref_cycle`` should be used as a reference for image registration.

The reference channel must be present in all *cycles*. The reference cycle should be the one used for image segmentation.

The resulting values and additional metainformation are stored in a `shift-descriptor`_ file in JSON format.


.. _shift-descriptor:

Shift descriptor
----------------

Calculated shift and overlap values are stored together with additional metainformation in **shiftDescriptor.json** files in JSON format. Each file contains the following key-value pairs:

.. code::

    {   
        "xShift": List[int],
        "yShift": List[int],
        "fileName": List[str],
        "lowerOverlap": int,
        "upperOverlap": int,
        "rightOverlap": int,
        "leftOverlap": int,
        "maxShift": int,
        "noShiftIndex": List[bool],
        "noShiftCount": int,
        "segmentationDirectory": str,
        "segmentationFileNameTrunk": str,
        "cycleNum": int
    }

**xShift**: A positive value means that the image is shifted to the right with respect to its reference image, while a negative value indicates a shift to the left. The unit is pixels.

**yShift**: A positive value means that the image is shifted downwards with respect to its reference image, while a negative value indicates an upwards shift. The unit is pixels.

**fileName**: The name of the image that was used as a reference upon registration.

**noShiftIndex**: true if the maximally tolerated shift value exceeded the actual shift value at this image site, false otherwise. This can for example happen in case of empty images. By default the **maxShift** value is set to 100 to avoid arbitrary large shifts at empty sites. You can overwrite this behavior and change the value using the ``-m`` or ``--max_shift`` argument.

**segmentationDirectory**: Relative path to the folder holding the segmentation images. By default this assumes that you want to use the shift description files for alignment in Jterator modules and sets the path relative to a Jterator project. You can overwrite this behavior and change the path using the ``--segm_dir`` command.

**segmentationFileNameTrunk**: The first part of the filename all image files of the same cycle have in common. This may be required for regular expressions operations. You can define this string using the ``--segm_trunk`` argument.

