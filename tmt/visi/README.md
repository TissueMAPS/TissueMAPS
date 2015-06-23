# visi #

Visi is a command line tool for converting **.stk** files from Visitron microscopes into **.png** images with optional file renaming.

For help, do
```{bash}
visi -h
```

Positional arguments:
- **run**: run stk to png conversion
- **joblist**: create a joblist YAML file for parallel processing

## Unpacking ##

To unpack *stk* files and convert them to *png* use the `run` argument:

```{bash}
visi run [stk_folder]
```

The *.png* image files will be written into a sibling folder of the input "STK" folder. By default, the output folder will by named "TIFF" (doesn't make sense I know, but let's stick to old conventions). You can change the name of the output folder using the `--output_folder_name` argument:

```{bash} 
visi run --output_folder_name [output_folder_name] [stk_folder]
```

If your input folder contains several *.nd* files, you might want to store the corresponding *.png* output files in separate folders. To this end, use the `-s` or `--split_output` argument:

```{bash}
visi run -s [stk_folder]
```

This will create separate folders in the output directory using the basename of each corresponding *.nd* file as folder name. Each of these folders will themselves contain a subfolder for the actual images.


## Renaming ##

You can rename the *.stk* files to encode certain information in the filename string.

If you want to rename files, use the `-r` or `--rename` argument:
```{bash}
visi run -r [stk_folder]
```

By default, images are renamed according standard configuration settings. You can choose keywords to format the filename strings. See [visi.config](visi.config)) for details. 

```{yaml}
NOMENCLATURE_FORMAT: '{project}_{well}_s{site:0>4}_r{row:0>2}_c{column:0>2}_z{zstack:0>2}_t{time:0>4}_{filter}_C{channel:0>2}.png'

ACQUISITION_MODE: 'ZigZagHorizontal'

ACQUISITION_LAYOUT: 'columns>rows'
```

If you want to rename files differently, you can use a custom config file. To this end, simply create a copy of the `visi.config` file (outside of this repository!) and modify it to your needs.

To use a custom config file and overwrite the default configuration settings, use the `-c` or `--config` argument:
```{bash}
visi run -r -c [config_filename] [stk_folder]
```

> NOTE: TissueMAPS requires the positional information "row" and "column" to be encoded in the filename!


## Parallel processing ##

If you don't want to process all *.stk* files one after another, you can specify which "job" should be processed.

This can be done by specifying individual jobs directly using the `-j` or `--job` argument (note that these job IDs are *one-based*!):

```{bash}
visi run -j [job_id] [stk_folder]
```

However, in order to run individual jobs you first need to create a **joblist**. A joblist is a file in *YAML* syntax that lists the files to be processed per job.

To create such a *.jobs* file, do:

```{bash}
visi joblist [stk_folder]
```

By default, the batch size (the number of files processed per job) is 10.
You can change this number using the `-b` or `--batch_size` argument:

```{bash}
visi joblist -b [batch_size] [stk_folder]
```

#### Usage on Brutus ####

The repository contains the example submission script [bsub_visi.py](tmt/visi/bsub_visi.py). You can create a copy of it (outside of this repository!) and adapt it to your needs.

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
