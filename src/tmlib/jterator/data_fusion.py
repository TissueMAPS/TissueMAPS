import pandas as pd
import numpy as np
from ..readers import DatasetReader
from ..errors import DataError


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
        object_names = f.list_group_names('/objects')

    for obj_name in object_names:
        features_path = obj_name + '/' + 'features'
        segmentation_path = obj_name + '/' + 'segmentation'
        metadata_path = '/images'
        data[features_path] = pd.DataFrame()

        for i, filename in enumerate(data_files):

            with DatasetReader(filename) as f:

                # TODO: deal with empty or missing datasets

                # TODO: parent objects for removal of border objects

                if f.exists(features_path):
                    dataset_names = f.list_dataset_names(features_path)
                    if dataset_names:
                        feature = pd.DataFrame()
                        for name in dataset_names:
                            dataset_path = '{group}/{dataset}'.format(
                                            group=features_path, dataset=name)
                            feature[name] = f.read(dataset_path)
                        if i == 0:
                            data[features_path] = feature
                        else:
                            data[features_path] = \
                                pd.concat([data[features_path], feature])

                if f.exists(metadata_path):
                    dataset_names = f.list_dataset_names(metadata_path)
                    for name in dataset_names:
                        metadata = pd.DataFrame()
                        dataset_path = '{group}/{dataset}'.format(
                                            group=metadata_path, dataset=name)
                        metadata[name] = f.read(dataset_path)
                        if i == 0:
                            data[metadata_path] = metadata
                        else:
                            data[metadata_path] = \
                                pd.concat([data[metadata_path], metadata])
                else:
                    raise DataError(
                            'Data file must contain group "%s"'
                            % metadata_path)

                if f.exists(segmentation_path):
                    dataset_names = f.list_dataset_names(segmentation_path)
                    for name in dataset_names:
                        dataset_path = '{group}/{dataset}'.format(
                                        group=segmentation_path, dataset=name)
                        if i == 0:
                            data[dataset_path] = f.read(dataset_path)
                        else:
                            data[dataset_path] = np.array(np.append(
                                data[dataset_path], f.read(dataset_path)
                            ), dtype=data[dataset_path].dtype)
                    group_names = f.list_group_names(segmentation_path)
                    for g_name in group_names:
                        group_path = '{group}/{subgroup}'.format(
                                        group=segmentation_path,
                                        subgroup=g_name)
                        dataset_names = f.list_dataset_names(group_path)
                        for name in dataset_names:
                            dataset_path = '{group}/{dataset}'.format(
                                            group=group_path, dataset=name)
                            if g_name == 'image_dimensions':
                                if i == 0:
                                    data[dataset_path] = f.read(dataset_path)
                            else:
                                if i == 0:
                                    data[dataset_path] = f.read(dataset_path)
                                else:
                                    data[dataset_path] = \
                                        np.array(
                                            np.append(
                                                data[dataset_path],
                                                f.read(dataset_path)
                                            ),
                                        dtype=data[dataset_path].dtype)

            # Remove individual data files
            # os.remove(filename)

        # remove duplicate columns
        data[features_path] = data[features_path].T.groupby(level=0).first().T

    return data


def create_object_layers(data_file):
    '''
    '''
