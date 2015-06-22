# datafusion #

Datafusion is a command line tool for fusing individual Jterator *.data* HDF5 files into one final `data.h5` HDF5 file. For each Jterator project there exists one data file per image.

For help, do
```{bash}
datafusion -h
```

Required (positional) arguments:    
* `experiment_dir`: full path to the experiment directory 

```{bash}
datafusion [experiment_dir]
```

## Input data files ##

The fusion step assumes that the *.data* files produced by Jterator internally have a flat hierarchy, i.e. that all datasets are stored in the root group of the file, and that each dataset should be a column vector of size *n*x1, where *n* is the number of objects. It further assumes that the names of the datasets encode the following information:

```
/[object]_[feature class]_[channel]_[feature]_[sub-feature]   Dataset {n} :: FLOAT
/[object]_[feature class]_[channel]_[feature]_[sub-feature]   Dataset {n} :: FLOAT
/[object]_[feature class]_[channel]_[feature]_[sub-feature]   Dataset {n} :: FLOAT

...
```
e.g.

```
Cells_Texture_DAPI_Haralick_Entropy
```

The keyword *channel name* is optional because some features are measured independent of a channel (intensity) image.

e.g.

```
Cells_AreaShape_Morphology_Area
```

This structure is defined on the level of Jterator modules! For more details on Jterator modules see [JtLib](https://github.com/pelkmanslab/JtLib).


### Required measurement datasets ###

There are a few measurements that are required for TissueMAPS and that differ from the above structure:

- **[object name]_OriginalObjectIds**: The IDs of the objects in the segmentation images. They are unique per image site.
- **[object name]_Centroids**: The y, x (row, column) coordinates of the geometric center of objects in the segmentation images.
- **[object name]_BorderIx**: The indices of objects that lie at the border of the images. 1 if the object touches the border, 0 otherwise.
- **[object name]_ParentIds**: The IDs of the corresponding parent objects. They are unique per image site.


## Output data file ##


The final `data.h5` file is structured as follows:

```
/

/objects                            Group
/objects/cells                      Group

/objects/cells                      Group
/objects/cells/ids                  Dataset {n}         :: INTEGER
/objects/cells/original-ids         Dataset {n, 4}      :: INTEGER  
/objects/cells/centroids            Dataset {n, 2}      :: INTEGER
/objects/cells/border               Dataset {n}         :: INTEGER (BOOLEAN)
/objects/cells/features             Dataset {n, p}      :: FLOAT

/objects/nuclei                     Group
/objects/nuclei/parent_ids          Dataset {n}         :: INTEGER
/objects/nuclei/ids                 Dataset {n}         :: INTEGER
/objects/nuclei/original-ids        Dataset {n, 4}      :: INTEGER
/objects/nuclei/centroids           Dataset {n, 2}      :: INTEGER
/objects/nuclei/border              Dataset {n}         :: INTEGER (BOOLEAN)
/objects/nuclei/features            Dataset {n, p}      :: FLOAT

```

where *n* is the number of objects and *p* is the number of features. The object names "cells" and "nuclei" are not hard-coded, but only serve as an example here.

The **ids** of each object are global and should map to the row number (one-based) in the corresponding features dataset. Each non-parent dataset (nuclei objects in the example above) should contain a dataset called **parent_ids** that indicates to which parent object each row in the sub-dataset belongs. This becomes particularly import if the number of children objects differs from the number of parent objects, i.e. if there are several children objects per parent.

The **original-ids** dataset contains for each object its *site*, *row*, *column*, and *object* id of each original individual images. This object id is site-specific in contrast to the global ids! The dataset has an attribute with the **names** of the ids.


The **features** datasets have an attribute called **names** of length *p* describing each feature. These feature names match the names of the  corresponding datasets in the input data files and are thus also of the form:

```
[object]_[feature class]_[channel]_[feature]_[sub-feature]
```

The **centroids** datasets have an attribute **names** of length 2 specifying the global "y" and "x" coordinate of each pixel in the stitched mosaic image. 


The **parent** dataset specifies the parent object (e.g. "cells" in the above example).

> NOTE: So far only implemented for objects with identical object counts!
