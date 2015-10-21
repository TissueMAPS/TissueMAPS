The *collect* step collects segmentations and measurements data created by individual jobs and fuses them into a single HDF5 file.

The final ``data.h5`` file is structured as follows:

.. code::

    /

    /objects                                    Group
    /objects/cells                              Group

    /objects/cells                              Group
    /objects/cells/ids                          Dataset {n}      :: INTEGER 32
    /objects/cells/parent_ids                   Dataset {n}      :: INTEGER 32
    /objects/cells/is_border                    Dataset {n}      :: BOOL
    /objects/cells/is_discarded                 Dataset {n}      :: BOOL
    /objects/cells/features                     Dataset {n, p}   :: FLOAT

    /objects/cells/segmentations                Group
    /objects/cells/segmentations/outlines       Group
    /objects/cells/segmentations/outlines/y     Dataset {n}      :: VARIABLE-LENGTH INTEGER 64
    /objects/cells/segmentations/outlines/x     Dataset {n}      :: VARIABLE-LENGTH INTEGER 64
    /objects/cells/segmentations/centroids      Group
    /objects/cells/segmentations/centroids/y    Dataset {n}
    /objects/cells/segmentations/centroids/x    Dataset {n}


where *n* is the number of objects, *m* is the maximal number of pixels along the perimeter of objects, and *p* is the number of features measured per object. The object names "cells" and "nuclei" only serve as an example here.
