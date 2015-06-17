## datafusion ##

Datafusion is a command line tool for fusing Jterator data from different sub-experiments (i.e. *cycles*) stored in individual HDF5 files into one final HDF5 file. 

The final `data.h5` file is structured as follows:

```
/

/parent                     Dataset {SCALAR}    :: STRING

/cells                      Group
/cells/ids                  Dataset {n}         :: STRING
/cells/centroids            Dataset {n, 2}      :: FLOAT
/cells/border               Dataset {n}         :: INTEGER (BOOLEAN)
/cells/features             Dataset {n, p}      :: FLOAT

/nuclei                     Group
/nuclei/parent_ids          Dataset {n}         :: INTEGER
/nuclei/ids                 Dataset {n}         :: STRING
/nuclei/centroids           Dataset {n, 2}      :: FLOAT
/nuclei/border              Dataset {n}         :: INTEGER (BOOLEAN)
/nuclei/features            Dataset {n, p}      :: FLOAT

```

where *n* is the number of objects and *p* is the number of features. The **ids** of each object should correspond to the row number (one-based) in the features dataset. Each non-parent dataset (e.g. nuclei in the example above) should contain a dataset called **parent_ids** that indicates to which parent object each row in the sub-dataset belongs.

The **features** datasets have an attribute called **names** of length *p* specifying the features (:: STRING) in the form:

```
[object name]_[feature class]_[layer name]_[feature name]_[sub-feature name]
```

e.g.

```
Cells_AreaShape_Morphology_Area
```

or 

```
Cells_Texture_DAPI_Haralick_entropy
```

The **centroids** datasets have an attribute **names** of length 2 specifying the global "y" and "x" coordinate of each pixel in the stitched mosaic image. 


The **parent** dataset specifies the parent object, e.g. "cells".

> Note: Data fusion is so far only implemented for objects with identical object counts.
