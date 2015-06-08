## datafusion ##

Datafusion is a command line tool for fusing Jterator data from different sub-experiments (i.e. *cycles*) stored in individual HDF5 files into one final HDF5 file.

The final `data.h5` file has the form:

```
/

/parent                     Dataset {SCALAR}    :: STRING

/cells                      Group
/cells/centroids            Dataset {n, 2}      :: FLOAT
/cells/boundaries           Dataset {n, 2}      :: INTEGER
/cells/border               Dataset {n}         :: INTEGER (BOOLEAN)
/cells/features             Dataset {n, p}      :: FLOAT

/nuclei                     Group
/nuclei/parent_ids          Dataset {n}         :: INTEGER
/nuclei/centroids           Dataset {n, 2}      :: INTEGER
/nuclei/boundaries          Dataset {n, 2}      :: INTEGER
/nuclei/border              Dataset {n}         :: INTEGER (BOOLEAN)
/nuclei/features            Dataset {n, p}      :: FLOAT

```

where *n* is the number of objects and *p* is the number of features.
The id of each object should correspond to the number of its row in the parent
data set.
Each non-parent data set (e.g. *nuclei* in the example above) should contain a
dataset called `parent_ids` that indicates to which parent object each row in
the sub dataset belongs.

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

The **centroids** and **boundaries** datasets each have an attribute **names** of length 2 specifying the 'y' and 'x' coordinate of each pixel per image site.
