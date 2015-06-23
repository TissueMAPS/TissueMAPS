# align #

Align is a command line tool for aligning images acquired at different acquisition "cycles", i.e. images acquired at the same site at different time points. These images might be shifted in y, x direction (no rotation and no scale).

For help, do
```{bash}
align -h
```

Positional arguments:
- **run**: run shift calculation
- **joblist**: create a joblist YAML file for parallel processing
- **fuse**: fuse calculated shifts, calculate overlaps, and create the shift descriptor JSON file

The information required for alignment is generated in two steps:     
1) **Image registration**: calculate shift between an image and a reference image (*run* step)
2) **Overlap calculation**: calculate the overlap of images after shifting (*fuse* step)

By default, registration is performed on images of channel number 1 relative to images from the last cycle, i.e. the subexperiment with highest cycle number. You can overwrite this by providing the `--ref_channel` and `--ref_cycle` arguments to specify from which acquisition channel images should be selected for registration and which acquisition cycle should be used as a reference, respectively.

The resulting values and additional metainformation are stored in a *shift descriptor* file in JSON format (see below).


## Shift descriptor files ##

Calculated shift and overlap values are stored together with additional metainformation in **shiftDescriptor.json** files in JSON format. Each file contains the following key-value pairs:

```{json}
{   
    "xShift": List[int],
    "yShift": List[int],
    "fileName": List[int],
    "lowerOverlap": int,
    "upperOverlap": int,
    "rightOverlap": int,
    "leftOverlap": int,
    "maxShift": int,
    "noShiftIndex": List[int],
    "noShiftCount": int,
    "segmentationDirectory": str,
    "segmentationFileNameTrunk": str,
    "cycleNum": int
}
```

**xShift**: A positive value means that the image is shifted to the right with respect to its reference image, while a negative value indicates a shift to the left. The unit is pixels.

**yShift**: A positive value means that the image is shifted downwards with respect to its reference image, while a negative value indicates an upwards shift. The unit is pixels.

**fileName*: The name of the image that was used as a reference upon registration.

**noShiftIndex**: 1 if the maximally tolerated shift value exceeded the actual shift value at this image site, 0 otherwise. This can for example happen for empty images. By default the **maxShift** value is set to 100 to avoid arbitrary large shifts at empty sites. You can overwrite this behavior and change the value using the `-m` or `--max_shift` argument.

**segmentationDirectory**: Relative path to the folder holding the segmentation images. By default this assumes that you want to use the shift description files for alignment in Jterator modules and sets the path relative to a Jterator project. You can overwrite this behavior and change the path using the `--segm_dir` command.

**segmentationFileNameTrunk**: The first part of the filename every image file of the same cycle has in common. This may be required for regular expression operations. You can set this string using the `--segm_trunk` argument.


## Parallel processing ##

If you don't want to process all images files one after another, you can specify which "job" should be processed.

This can be done by specifying individual jobs directly using the `-j` or `--job` argument (note that these job IDs are *one-based*!):

```{bash}
align run -j [job_id] [experiment_folder]
```

However, in order to run individual jobs you first need to create a **joblist**. A joblist is a file in *YAML* syntax that lists the files to be processed per job.

To create such a *.jobs* file, do:

```{bash}
visi joblist [experiment_folder]
```

By default, the batch size (the number of files processed per job) is 10.
You can change this number using the `-b` or `--batch_size` argument:

```{bash}
align joblist -b [batch_size] [experiment_folder]
```

#### Usage on Brutus ####

The repository contains the example submission script [bsub_align.py](tmt/align/bsub_align.py). You can create a copy of it (outside of this repository!) and adapt it to your needs.

On Brutus you will need to load Python and, depending on your configuration,you may also have to install some additional Python packages.

To load python, do:
```{bash}
module load python/2.7.2
```

You can also put the above line in your .bash_profile file to always load Python when you connect to Brutus.

To install packages do:
```{bash}
pip install [package_name] --user
```

