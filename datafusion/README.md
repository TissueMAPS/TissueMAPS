## datafusion ##

Datafusion is a command line tool for fusing Jterator data from different sub-experiments (i.e. *cycles*) stored in individual HDF5 files into one final HDF5 file.

The final `data.h5` file has the form:

```
/

/objects                    Group
/objects/cells                      Group

/objects/cells/ids                  Dataset {n}         :: INTEGER
/objects/cells/parent               Dataset {SCALAR}    :: STRING
/objects/cells/centroids            Dataset {n, 2}      :: FLOAT
/objects/cells/border               Dataset {n}         :: INTEGER (BOOLEAN)
/objects/cells/features             Dataset {n, p}      :: FLOAT

/objects/nuclei                     Group
/objects/nuclei/ids                 Dataset {n}         :: INTEGER
/objects/nuclei/parent              Dataset {SCALAR}    :: STRING
/objects/nuclei/parent_ids          Dataset {n}         :: INTEGER
/objects/nuclei/centroids           Dataset {n, 2}      :: FLOAT
/objects/nuclei/border              Dataset {n}         :: INTEGER (BOOLEAN)
/objects/nuclei/features            Dataset {n, p}      :: FLOAT

```

where *n* is the number of objects and *p* is the number of features.
The id of each object should correspond to the number of its row in the parent data set.
Each data set contains a scalar string dataset called *parent* that indicates to which parent object each row in the sub dataset belongs.
For example: the object *nuclei* above would have `'parent'` as its parent entry.
The entry `parent_ids` then lists the id of the parent (cell) object to which each child object (nuclei) belongs.
The topmost object has an empty string as its parent entry and also no `parent_ids` entry.

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

The **parent** dataset specifies the parent object, e.g. "Cells".

> Note: Data fusion is so far only implemented for objects with identical object counts.

The **ids** dataset consists of strings that specify a global id of the form:

```
[row number]-[column number]-[site-specific id]
```

The **centroids** dataset has an attribute **names** of length 2 specifying the 'y' and 'x' coordinate of each pixel per image site.
