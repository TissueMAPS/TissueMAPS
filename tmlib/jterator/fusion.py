import pandas as pd
import numpy as np
from ..readers import DatasetReader


def fuse_datasets(data_files):
    '''
    Fuse Jterator data of one project stored across several HDF5 files.

    Parameters
    ----------
    data_files: List[str]
        paths to Jterator data files

    Returns
    -------
    Dict[pandas.core.frame.DataFrame]
        fused datasets of *features* groups with dimensions nxp,
        where n is the number of objects and p the number of features,
        for each object type
    '''
    data = dict()
    with DatasetReader(data_files[0]) as f:
        object_names = f.list_group_names('/')

    for obj_name in object_names:
        features_path = obj_name + '/' + 'features'
        segmentation_path = obj_name + '/' + 'segmentation'
        data[features_path] = pd.DataFrame()

        for i, filename in enumerate(data_files):

            with DatasetReader(filename) as f:

                # TODO: deal with empty or missing datasets

                # TODO: parent objects for removal of border objects

                if f.exists(features_path):
                    dataset_names = f.list_dataset_names(features_path)
                    if dataset_names:
                        feature = pd.DataFrame()
                        for feat_name in dataset_names:
                            feature[feat_name] = \
                                f.read(features_path + '/' + feat_name)
                        if i == 0:
                            data[features_path] = feature
                        else:
                            data[features_path] = \
                                pd.concat([data[features_path], feature])

                if f.exists(segmentation_path):
                    dataset_names = f.list_dataset_names(segmentation_path)
                    for segm_name in dataset_names:
                        dataset_path = '%s/%s' % (segmentation_path, segm_name)
                        if segm_name == 'image_dimensions':
                            if i == 0:
                                data[dataset_path] = f.read(dataset_path)
                        else:
                            if i == 0:
                                data[dataset_path] = f.read(dataset_path)
                            else:
                                data[dataset_path] = np.array(np.append(
                                    data[dataset_path], f.read(dataset_path)
                                ), dtype=data[dataset_path].dtype)

        # remove duplicate columns
        data[features_path] = data[features_path].T.groupby(level=0).first().T

    return data
