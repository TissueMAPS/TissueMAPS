# corilla

Corilla is a command line tool for calculating statistics in order to **COR**ect **ILL**umination **A**rtifacts of fluorescence microscopy images as described in [1]. It uses an online algorithm based on Welford's method [2] for the calculation of mean and standard deviation at each pixel position across a large set of images.

For help, do
```{bash}
corilla -h
```

Positional arguments:
- **run**: run statistics calculation
- **submit**: submit jobs for statistics calculation on a cluster
- **apply**: apply calculated statistics to images in order to correct them for illumination artifacts

In order to calculate illumination statistics for all channels of your project, do

```{bash}
corilla run [project_dir]
```

## Output

Mean and standard deviation matrices are stored in an HDF5 file per channel.
The name of this file is defined in the configuration settings in `tmt.config`.

Internally the HDF5 file is structured as follows:

```
/
/statistics                         Group
/stat_values/mean                   Dataset {p, q}         :: DOUBLE
/stat_values/std                    Dataset {p, q}         :: DOUBLE
```

> NOTE: The previous calculations were done in Matlab. Matlab transposes arrays upon writing to and reading from HDF5. Corilla doesn't do this!

## References

[1] Stoeger T, Battich N, Herrmann MD, Yakimovich Y, Pelkmans L. 2015. "Computer vision for image-based transcriptomics". Methods.

[2] Welford BP. 1962. "Note on a method for calculating corrected sums of squares and products". Technometrics.
