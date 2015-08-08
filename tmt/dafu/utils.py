import h5py
import re
import os
import glob
import natsort
import numpy as np
import pandas as pd


def extract_ids(data_file, current_obj):
    '''
    Extract ids of the currently analyzed objects and their parent objects
    from the dataset. They represent the original local ids, i.e. they map to
    objects in single acquisition site images rather in contrast to global ids
    which map to objects in the stitched mosaic image.
    These local ids can be used to discard certain objects,
    such as border objects, from single site images before stitching.

    Parameters
    ----------
    data_file: str
        path to data.h5 HDF5 file that contains the dataset
    current_obj: str
        name of currently analyzed objects

    Returns
    -------
    Tuple[pandas.core.frame.DataFrame]
        with ids for current objects and their corresponding parent objects
    '''

    f = h5py.File(data_file, 'r')

    parent_obj = f['parent'][()].lower()  # lower case!
    parent = pd.DataFrame(f['objects/%s/original-ids' % parent_obj][()])
    parent.columns = f['objects/%s/original-ids' % parent_obj].attrs['names'][()]
    parent['IX_border'] = f['objects/%s/border' % parent_obj][()]

    current = pd.DataFrame(f['objects/%s/original-ids' % current_obj][()])
    current.columns = f['objects/%s/original-ids' % current_obj].attrs['names'][()]
    current['ID_global'] = f['objects/%s/ids' % current_obj][()]

    if current_obj != parent_obj:
        current['ID_parent'] = f['objects/%s/original-parent-ids' % current_obj][()]
    else:
        current['ID_parent'] = current['ID_object']

    f.close()

    return (current, parent)


def build_global_ids(ids):
    '''
    Build global, continuous ids from local, image site specific ids.

    Parameters
    ----------
    ids: pandas.core.frame.DataFrame
        dataset of size nx4 with the following columns:
        "{object name}_ID_site"
        "{object name}_ID_row"
        "{object name}_ID_column"
        "{object name}_ID_object"

    Returns
    -------
    pandas.core.series.Series
    '''
    n_row = int(np.max(ids.filter(regex='^[^_]+_ID_row')))
    n_col = int(np.max(ids.filter(regex='^[^_]+_ID_column')))
    obj_global_ids = ids['ID_object'].copy()

    offset = 0
    for r in range(1, n_row+1):
        for c in range(1, n_col+1):
            ix = (ids.ID_row == r) & (ids.ID_column == c)
            local_ids = ids['ID_object'][ix]
            obj_global_ids[ix] = local_ids + offset
            offset = np.max(local_ids + offset)

    return obj_global_ids


def calc_global_centroids(local_centroids, ids, image_size):
    '''
    Calculate global centroids from local, image site specific coordinates.

    Parameters
    ----------
    local_centroids: pandas.core.frame.DataFrame
        size nx2, where n is the number of
        objects, and the columns are the y, x coordinates
        of each object at the local site (i.e. in the image)
    ids: pandas.core.frame.DataFrame
        dataset of size nx4 with the following columns:
        "{object name}_ID_site"
        "{object name}_ID_row"
        "{object name}_ID_column"
        "{object name}_ID_object"
    image_size: Tuple[int]
        dimensions of an individual image, i.e. site

    Returns
    -------
    pandas.core.frame.DataFrame
        dataset with dimensions nx2 and columns "y" and "x"
    '''
    n_row = int(np.max(ids.filter(regex='^[^_]+_ID_row')))
    n_col = int(np.max(ids.filter(regex='^[^_]+_ID_column')))
    global_centroids = local_centroids.copy()  # new creates indexing problems?
    global_centroids.columns = ['y', 'x']

    y_offset = 0
    x_offset = 0
    for r in range(1, n_row+1):
        for c in range(1, n_col+1):
            ix = (ids.ID_row == r) & (ids.ID_column == c)
            global_centroids['y'][ix] = local_centroids[0][ix] + y_offset
            global_centroids['x'][ix] = local_centroids[1][ix] + x_offset
            y_offset = np.max(image_size[0] + y_offset)
            x_offset = np.max(image_size[1] + x_offset)

    return global_centroids


def list_jtprojects(cycle_dir):
    '''
    Returns
    -------
    List[str]
        names of Jterator projects
    '''
    return [f for f in os.listdir(cycle_dir)
            if os.path.isdir(os.path.join(cycle_dir, f))
            and glob.glob(os.path.join(cycle_dir, f, '*.pipe'))]


def image_name_from_joblist(joblist, data_filename):
    '''
    Determine the name of an image file from a YAML joblist description.

    Parameters
    ----------
    joblist: List[Dict[str, str]]
        joblist description for each job
    data_filename: str
        name of a data HDF5 file that encodes the job id

    Returns
    -------
    str
        filename
    '''
    job_id = int(re.search(r'_(\d+).data$', data_filename).group(1).lstrip('0'))
    return joblist[(job_id-1)].values()[0]  # convert to zero-based indexing!


def list_data_files(project_dir):
    '''
    Provide a sorted list of data HDF5 files of a given Jterator project.

    Parameters
    ----------
    project_dir: str
        path to a Jterator project directory

    Returns
    -------
    List[str]
        names of data files
    '''
    return natsort.natsorted(glob.glob(os.path.join(project_dir,
                                                    'data', '*.data')))
