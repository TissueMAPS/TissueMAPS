Command line interface
----------------------

Fuse data stored across individual `Jterator <https://github.com/TissueMAPS/Jterator>`_ *.data* HDF5 files into one final ``data.h5`` HDF5 file. For each Jterator project there exists one *.data* file per job, which generally corresponds to one image.

For help, do

.. code::

    $ dafu -h


Input data files
----------------

The fusion step assumes that the *.data* files produced by Jterator internally have a flat hierarchy, i.e. that all datasets are stored in the root group of the file, and that each dataset should be a column vector of size *n*x1, where *n* is the number of objects. The only exception to that rule are the *outline* datasets (see below). It further assumes that the names of the datasets encode the following information:

.. code::

    /[object]_[feature class]_[channel]_[feature]_[sub-feature]   Dataset {n} :: FLOAT
    /[object]_[feature class]_[channel]_[feature]_[sub-feature]   Dataset {n} :: FLOAT
    /[object]_[feature class]_[channel]_[feature]_[sub-feature]   Dataset {n} :: FLOAT

    ...

e.g. ``Cells_Texture_DAPI_Haralick_Entropy``


The keyword *channel* is optional because some features are measured independent of a channel (intensity) image.

Similarly, there mustn't be a *sub-feature* keyword, because some features don't have sub-features.

e.g. ``Cells_Morphology_Area``


This structure is defined on the level of Jterator modules! For more details on these modules see `JtLib <https://github.com/TissueMAPS/JtLibrary>`_.


Required datasets
-----------------

There are a few measurements that are required for TissueMAPS:

- **[object name]_OriginalObjectId**: The IDs of the objects in the segmentation images. They are unique per image site. The dataset is created by the *align_objects.py* module.
- **[object name]_ParentId**: The IDs of the corresponding parent objects. They are unique per image site. The dataset is created by the *relate_objects.py* module.
- **[object name]_Centroid_y** and **[object name]_Centroid_x**: The y, x (row, column) coordinates of the geometric center of objects in the segmentation images. The dataset is created by the *measure_position.py* module.
- **[object name]_BorderIx**: The indices of objects that lie at the border of the images. 1 if the object touches the border, 0 otherwise. The dataset is created by the *measure_position.py* module.
- **[object name]_Outline_y** and **[object name]_Outline_x**: The y, x (row, column) coordinates of the contour of objects in the segmentation images. The dataset is created by the *measure_position.py* module (with ``outlines=True`` option).


Output data file
----------------

The final ``data.h5`` file is structured as follows:

.. code::

    /

    /objects                            Group
    /objects/cells                      Group

    /objects/cells                      Group
    /objects/cells/ids                  Dataset {n}         :: INTEGER
    /objects/cells/original-ids         Dataset {n, 4}      :: INTEGER  
    /objects/cells/centroids            Dataset {n, 2}      :: INTEGER
    /objects/cells/outlines-y           Dataset {n, m}      :: INTEGER
    /objects/cells/outlines-x           Dataset {n, m}      :: INTEGER
    /objects/cells/border               Dataset {n}         :: BOOLEAN
    /objects/cells/features             Dataset {n, p}      :: FLOAT

    /objects/nuclei                     Group
    /objects/nuclei/parent_ids          Dataset {n}         :: INTEGER
    /objects/nuclei/ids                 Dataset {n}         :: INTEGER
    /objects/nuclei/original-ids        Dataset {n, 4}      :: INTEGER
    /objects/nuclei/centroids           Dataset {n, 2}      :: INTEGER
    /objects/nuclei/outlines-y          Dataset {n, m}      :: INTEGER
    /objects/nuclei/outlines-x          Dataset {n, m}      :: INTEGER
    /objects/nuclei/border              Dataset {n}         :: BOOLEAN
    /objects/nuclei/features            Dataset {n, p}      :: FLOAT


where *n* is the number of objects, *m* is the maximal number of pixels along the perimeter of objects, and *p* is the number of features measured per object. The object names "cells" and "nuclei" only serve as an example here.


The **ids** of each object are global and should map to the row number (one-based) in the corresponding features dataset. Each non-parent dataset (nuclei objects in the example above) should contain a dataset called **parent_ids** that indicates to which parent object each row in the sub-dataset belongs. This becomes particularly import if the number of children objects differs from the number of parent objects, i.e. if there are several children objects per parent.

The **original-ids** dataset contains for each object its *site*, *row*, *column*, and *object* id of each original individual images. This object id is site-specific in contrast to the global ids! The dataset has an attribute with the **names** of the ids.


The **features** datasets have an attribute called **names** of length *p* describing each feature. These feature names match the names of the  corresponding datasets in the input data files and are thus also of the form:
``[object]_[feature class]_[channel]_[feature]_[sub-feature]``

The **centroids** datasets have an attribute **names** of length 2 specifying the global "y" and "x" coordinate of each pixel in the stitched mosaic image. 


The **parent** dataset specifies the parent object (e.g. "cells" in the above example).

    
    So far only implemented for objects with identical object counts!
