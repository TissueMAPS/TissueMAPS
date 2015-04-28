import re
from glob import glob
from os import listdir
from os.path import (join, isdir, basename)
from natsort import natsorted
import numpy as np
from scipy import misc
from image_registration import chi2_shift


def get_cycle_dirs(project_dir):
    '''
    Get directories of image acquisition cycles.

    Input:
        :project_dir:       absolute path to project folder

    Output:
        :cycle_dirs:        list of subdirectories of the project folder
                            containing the images

    Naming convention:
    ------------------
    The cycle directories have to be subdirectories of the project directory.
    They are further assumed to have the same basename as the project directory
    with the addition of a number at the end.

    Example:
        /150428myproject
            /150428myproject_01
            /150428myproject_02
            ...
    '''
    project_basename = basename(project_dir)
    r = re.compile('%s[_-]\d+$' % project_basename)
    cycle_dirs = [d for d in listdir(project_dir)
                  if re.search(r, d) and isdir(join(project_dir, d))]
    # Sort directories 'naturally', i.e. 1, 2, ... 10, 11, ..., 100, 101, ...
    cycle_dirs = natsorted(cycle_dirs)
    # Make paths absolute
    cycle_dirs = [join(project_dir, d) for d in cycle_dirs]
    return cycle_dirs


def get_image_filenames(cycle_dirs, ref_channel):
    '''
    Get filenames of the images, which should be aligned.

    Input:
        :cycle_dirs:        list of subdirectories of the project folder
                            containing the images

        :ref_channel:       reference channel for image registration (integer)

    Output:
        :image_filenames:   list of image filenames per cycle (list of lists)

    Naming convention:
    ------------------
    Images are assumed to reside in a folder called 'TIFF', which is a
    subdirectory of each cycle directory.

    Example:
        /150428myproject
            /150428myproject_01
                /TIFF
            /150428myproject_02
            ...
    '''
    # Here a few things are hard-coded. Consider replacing them with variables!
    image_filenames = list()
    for subproject in cycle_dirs:
        # Only list image filenames that match the reference channel number
        files = glob(join(subproject, 'TIFF', '*%.2d.png' % ref_channel))
        files = natsorted(files)
        image_filenames.append(files)
    # Make sure each subproject has the same number of filenames
    num_of_files = [len(files) for files in image_filenames]
    if len(np.unique(num_of_files)) > 1:
        raise Exception('Subprojects contain different number of image files.')
    return image_filenames


def calculate_shift(filename, ref_filename):
    '''
    Calculate shift between two images from different cycles.

    Input:
        :filename:          absolute path to image that should be registered

        :ref_filename:      absolute path to image that should be used as
                            a reference for registration

    Output:
        :x:                 shift in x direction (integer)
        :y:                 shift in y direction (integer)


    "Apparently astronomical images look a lot like microscopic images." [*]

    [*] http://image-registration.readthedocs.org/en/latest/
    '''
    # Load image that should be registered
    im = np.array(misc.imread(filename), dtype='float64')
    # Load reference image
    ref_im = np.array(misc.imread(ref_filename), dtype='float64')
    # Calculate shift between images
    (x, y, a, b) = chi2_shift(im, ref_im)
    return [x, y]
