# Illuminati #

Illuminati is a tool for creation of pyramids in [zoomify](http://www.zoomify.com/) format. In addition, it can be used to perform several custom image processing tasks, such as correcting images for illumination artifacts, shifting images for alignment between cycles, and rescaling images for convenient display.

The file *illuminati* represents the command line interface that combines the different routines. For help, do

```{bash}
illuminati -h
```

## Common use cases ##

The following sections provide a short example of how the tools would be used. For all supported options and default values see the tools help.

Illuminati allows you to create pyramid images and apply different pre-processing routines "on-the-fly", without having to save intermediate steps to disk. 

For example, in order to create a pyramid image of individual images corrected for illumination `-i`, shifted `-s` and thresholded `-t` (for rescaling purposes), you can call the following command:

```{bash}
illuminati ./ -w *C01.png -sit
```

The `-w` or `--wildcard` argument is required to select a subset of images within the image folder, in this example all images of channel 1.

To create a pyramid image of object outlines from individual segmentation images use the `-m` argument:

```{bash}
illuminati ./ -w *segmentedCells*.png -m
```

If you want to run a custom project, i.e. if your project layout deviates from the default *tmt* configuration, you can create a custom configuration file `-c` and use it by calling the following command:

```{bash}
illuminati ./ -w *C01*png -sit -c [config_filename]
```

Output directories for the different types of pyramids are dynamically determined from the configuration settings. However, you can also specify a different output directory:

```{bash}
illuminati ./ -w *C01*png -sit -o [output_dir]
```

If you want the program to only create the stitched mosaic image (without creating a pyramid) you can use the `--stitch_only` argument:

```{bash}
illuminati ./ -w *C01*png -sit --stitch_only -o [output_dir]
```

In this case you have to explicitly provide an output directory.

## Vips ##

Illuminati uses the image processing library [VIPS](http://www.vips.ecs.soton.ac.uk/index.php?title=VIPS) ([API](http://www.vips.ecs.soton.ac.uk/supported/current/doc/html/libvips/index.html)). It can be conveniently installed via homebrew (or other package managers). 

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

The [VIPS function list](http://www.vips.ecs.soton.ac.uk/supported/current/doc/html/libvips/func-list.html) can be useful as well.
