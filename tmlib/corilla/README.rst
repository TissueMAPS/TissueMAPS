Command line interface
----------------------

Calculate and apply statistics for **COR**\ecting **ILL**\umination **A**\rtifacts in fluorescence microscopy images as described in `[1]`_. It uses an online algorithm based on Welford's method `[2]`_ for the calculation of mean and standard deviation at each pixel position across a large set of images.

For help, do

.. code::

    $ corilla -h


Positional arguments:

- **run**: run statistics calculation
- **submit**: submit jobs for parallel calculation
- **apply**: apply calculated statistics to images in order to correct them for illumination artifacts


Output
------

Mean and standard deviation matrices are stored in an HDF5 file per channel.
The name of this file is defined in the configuration settings in `tmlib.cfg`.

Internally the HDF5 file is structured as follows:

.. code::

    /
    /data                               Group
    /data/mean                          Dataset {p, q}         :: DOUBLE
    /data/std                           Dataset {p, q}         :: DOUBLE
    /metadata                           Group
    /metadata/channel                   Dataset {1}            :: STRING
    /metadata/std                       Dataset {1}            :: STRING


References
----------

.. _[1]:

[1] Stoeger T, Battich N, Herrmann MD, Yakimovich Y, Pelkmans L. 2015. "Computer vision for image-based transcriptomics". Methods.

.. _[2]:

[2] Welford BP. 1962. "Note on a method for calculating corrected sums of squares and products". Technometrics.
