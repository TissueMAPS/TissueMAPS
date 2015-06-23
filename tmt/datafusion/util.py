import h5py
import pandas as pd


def extract_ids(data_file, current_obj):
    '''
    Extract ids of the currently analyzed objects and their parent objects
    from the dataset. They represent the original local ids, i.e. they map to
    objects in single acquisition site images rather in contrast to global ids
    which map to objects in the stitched mosaic image.
    These local ids can be used to discard certain objects,
    such as border objects, from single site images before stitching.

    Parameters:
    -----------
    data_file: str
               path to data.h5 HDF5 file that contains the dataset
    current_obj: str
                 name of currently analyzed objects

    Returns:
    --------
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
