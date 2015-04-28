# Illuminati #

Illuminati is a tool for pre-processing images for tissueMAPS. It stitches individual images and creates pyramids in [zoomify](http://www.zoomify.com/) format. In addition, it can be used to perform several custom image processing tasks, such as correcting images for illumination artifacts, shifting images for alignment between cycles, and rescaling images for convenient display.

The file *illuminati* represents the command line tool that combines the different routines. Each of the .py files provides the individual subroutines, such as: 
* illumination correction    
* stitching   
* thresholding (rescaling) 
* creation of outline masks   

These files can also be used as a command line tool (if called as the main module). See below for more details on these subroutines.

## How to use it ##

The following sections provide a short example of how the tools would be used. For all supported options and default values see the tools help, which can be displayed with, e.g.: 

```{bash}
illuminati -h
```

Illuminati allows you to create pyramid image and apply different pre-processing routines "on-the-fly", without having to save intermediate steps to disk. 

For example, in order to create a pyramid image of individual images corrected for illumination `-i`, shifted `-s` and thresholded for rescaling `-t`, you can call the following command:

```{bash}
illuminati TIFF/*C01.png -sit -o folder_of_pyramid
```

Or to create a pyramid image of object outlines from individual segmentation images using the `-m` command:

```{bash}
illuminati SEGMENTATION/*segmentedCells*.png -m -o folder_of_pyramid
```

If you want to run a custom project, i.e. if your project layout deviates from the default, you can create a custom configuration file `-c` and use it by calling the following command:

```{bash}
illuminati TIFF/*C01*png -sit -o folder_of_pyramid -c config_filename
```

## Dependencies ##

### Python packages



### Vips ###

Some of the pre-processing tools use the image processing library [VIPS](http://www.vips.ecs.soton.ac.uk/index.php?title=VIPS) ([API](http://www.vips.ecs.soton.ac.uk/supported/current/doc/html/libvips/index.html)), which can be conveniently installed via homebrew (or other package managers). 

On Mac OSX:   
```{bash}
brew install vips
```
Since VIPS is used from python, you also need to install the required python package [pygobject](https://wiki.gnome.org/action/show/Projects/PyGObject?action=show&redirect=PyGObject). You can do this via pip.
  
```{bash}
pip install pygobject3
```

You also need to set the `GI_TYPELIB_PATH` variable.


The Python wrapper for VIPS is based on GObject introspection. The type definitions are therefore automatically loaded and can be used from within Python, but there are also some convenience functions that are added to the `Image` class and some other shortcuts (like the automatic conversions of Python strings like `'horizontal'` to the respective C constants).
In IPython these convenience functions won't show up when TAB completing on the image object. For example:

The C function

    int
    vips_add (VipsImage *left,
              VipsImage *right,
              VipsImage **out,
              ...);

is added to the Python image objects, but won't show up. The docs can still be displayed with `?img.add`, however.

For more information see [VIPS from Python](http://www.vips.ecs.soton.ac.uk/supported/current/doc/html/libvips/using-from-python.html).


### Sub-routines ###


#### illumcorrect.py ####

TissueMAPS tool for correcting images for illumination artifacts.

    $ illumcorrect.py --help

    $ illumcorrect.py *.png -o folder_of_corrected_images

This will create images with the same name as their original but with an added suffix (by default '-corr').


#### segment.py ####

TissueMAPS tool for computing coordinates of outline polygons for all cells that then could be used as overlays to mark the cells.
At this point in time, polygonal features aren't supported in openlayers when using the WebGL renderer, so it's not clear how useful this really is.
The files that need to be supplied to the tool should be matrices where contiguous blocks of the same number indicate a cell.

    $ segment.py *.png -o outlines.hdf5


#### stitch.py ####

TissueMAPS tool for stitching individual images together to one large image.
Images can optionally be shifted if required.

    $ stitch.py --help

Stitching is the process of creating a large image from many small ones. The file name of each small image tells the stitcher where it should be placed in the resulting large image. The file `config.yaml` holds regular expressions that are used to extract this information (see below).

Stitching and shifting the image in one go:

    $ stitch.py *DAPI*.png -s -o stitched_image_filename


#### pyramidize.py ####

TissueMAPS tool for creating a "zoomify" pyramid of a stitched image.

    $ pyramidize.py --help

    $ pyramidize.py some_large_image.png -o folder_of_the_pyramid

Pyramids are built using VIPS.


### YAML configuration file ###

Illuminati assumes a few things about your project layout, such as file naming convention and folder structure. These variables are defined in the [config.yaml](config.yaml) file and can be changed by the user for customization.

Note that the parenthesis around a string `" string "` value are not necessary, but it is advised to use them in this file due to the complexity of regular expression pattern strings to prevent things to get screwed-up!
