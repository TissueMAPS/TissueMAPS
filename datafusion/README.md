## datafusion ##

Datafusion is a command line tool for fusing Jterator data stored in individual HDF5 files per image into one final HDF5 file. 

The final `data.h5` file is structured as follows:

```
/

/parent                     Dataset {SCALAR}    :: STRING

/cells                      Group
/cells/ids                  Dataset {n}         :: INTEGER
/cells/original-ids         Dataset {n, 4}      :: INTEGER  
/cells/centroids            Dataset {n, 2}      :: INTEGER
/cells/border               Dataset {n}         :: INTEGER (BOOLEAN)
/cells/features             Dataset {n, p}      :: FLOAT

/nuclei                     Group
/nuclei/parent_ids          Dataset {n}         :: INTEGER
/nuclei/ids                 Dataset {n}         :: INTEGER
/nuclei/original-ids        Dataset {n, 4}      :: INTEGER
/nuclei/centroids           Dataset {n, 2}      :: INTEGER
/nuclei/border              Dataset {n}         :: INTEGER (BOOLEAN)
/nuclei/features            Dataset {n, p}      :: FLOAT

```

where *n* is the number of objects and *p* is the number of features. The object names "cells" and "nuclei" are not hard-coded, but serve as examples here.

The **ids** of each object should map to the row number (one-based) in the corresponding features dataset. Each non-parent dataset (e.g. nuclei in the example above) should contain a dataset called **parent_ids** that indicates to which parent object each row in the sub-dataset belongs.

The **original-ids** dataset contains for each object its *site*, *row*, *column*, and *object* id of each original individual images. It has an attribute with the **names** of the ids.

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
