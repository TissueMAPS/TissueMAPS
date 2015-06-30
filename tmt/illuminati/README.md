# Illuminati #

Illuminati is a tool for creation of pyramids in [zoomify](http://www.zoomify.com/) format. In addition, it can be used to perform several custom image processing tasks, such as correcting images for illumination artifacts, shifting images for alignment between cycles, and rescaling images for convenient display.

The file *illuminati* represents the command line interface that combines the different routines. For help, do

```{bash}
illuminati -h
```

Positional arguments:
- **channel**: creation of "channel" layers
- **mask**: creation of "mask" layers
- **lut**: creation of id lookup tables

## Usage ##

The following sections provide a short example of how the tools would be used. For all supported options and default values see the tools help.

### Creating channel layers ###

Illuminati allows you to create pyramid images and apply different pre-processing routines "on-the-fly", without having to save intermediate steps to disk. 

For example, in order to create a pyramid for a channel layer corrected for illumination `-i` and thresholded `-t` (for rescaling), do

```{bash}
illuminati channel -n [channel_number] -it [project_dir]
```

The `-n` or `--channel_nr` argument is required to select the subset of images belonging to the same channel, in this example all images of channel 1.

If you want to run a custom project, i.e. if your project layout deviates from the default *tmt* configuration, you can create a custom configuration file using the `-c` command

```{bash}
illuminati channel -n [channel_number] -it -c [config_filename] [project_dir]
```

Output directories for the different types of pyramids are dynamically determined from the configuration settings. However, you can also specify a different output directory:

```{bash}
illuminati channel -n [channel_nr] -it -o [output_dir] [project_dir]
```

If you want the program to only create the stitched mosaic image (without creating a pyramid) you can use the `--stitch_only` argument:

```{bash}
illuminati channel -n [channel_nr] -it --stitch_only -o [output_dir] [project_dir]
```

In this case you have to explicitly provide the path to the output directory.


### Creating mask layers ###

To create a pyramid image of object outlines from individual segmentation images, do

```{bash}
illuminati mask -n [objects_name] [project_dir]
```

#### Creating global cell id layer ####

This layer is not for direct visualization. It is rather used for "on-the-fly" colorization with the values returned by tools, such as the labels of a classifier.

```{bash}
illuminati mask -n [objects_name] --make-global-ids --png --no-rescale [project_dir]
```

This creates an 16bit RGB pyramid.

### Creating ID lookup tables ###

These files are required to identify the ID of an object, when the user clicks on a pixel on the mask belonging to that object. They represent int32 numpy arrays and are named as the corresponding segmentation files.


```{bash}
illuminati lut -n [objects_name] [project_dir]
```
