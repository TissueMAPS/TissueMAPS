********************************
Frequently Asked Questions (FAQ)
********************************


Why don't you use HDF5 as a container for all data?
---------------------------------------------------

`HDF5 <https://support.hdfgroup.org/HDF5/>`_ is a great format with efficient I/O under certain conditions, but there are some issues:

    - Datasets within a file cannot be deleted. They are only unlinked, but still occupy disk space. This makes the format not well suited for dynamic data that changes frequently.
    - I/O performance drops significantly when compression filters are used. Performance becomes comparible to that of *PNG* files at similar compression levels.
    - I/O performance also drops dramatically upon random access, i.e. when only small subsets of datasets are accessed. This becomes a bottleneck with complex access patterns.
    - No support for concurrent writes. As with every file format, locks prevent multiple processes from writing to a file in parallel. Ok, there is `Parallel HDF5 <https://support.hdfgroup.org/HDF5/PHDF5/>`_, but it relies on `MPI <http://mpi-forum.org/>`_ and who want's to use it these days? We don't! It wouldn't play nice with architectures like `Spark <http://spark.apache.org/>`_. In a distributed environment one would consequently have to use a separate file for each batch job (already a nightmare from a data consistency point of view).

There is a nice blog on this topic called `Moving away from HDF5 <http://cyrille.rossant.net/moving-away-hdf5/>`_.

We still use *HDF5* files, but only for large binary persistent data. However, we will probably also move to other formats for this use case in the future.


Does *TissueMAPS* run on GPUs?
------------------------------


