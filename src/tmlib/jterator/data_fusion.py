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
        object_names = f.list_groups('/objects')

    for i, filename in enumerate(data_files):

        with DatasetReader(filename) as f:

            # Collect metadata per site, i.e. per job ID
            metadata_path = '/metadata'

            if not f.exists(metadata_path):
                raise DataError(
                        'Data file must contain group "%s"' % metadata_path)

            job_ids = map(int, f.list_groups(metadata_path))
            for j in job_ids:
                j_group = '{group}/{subgroup}'.format(
                                group=metadata_path, subgroup=str(j))
                dataset_names = f.list_datasets(j_group)
                for name in dataset_names:
                    dataset_path = '{group}/{dataset}'.format(
                                        group=j_group, dataset=name)
                    data[dataset_path] = f.read(dataset_path)

            # Collect features and segmentations per object
            for obj_name in object_names:
                features_path = 'objects/%s/features' % obj_name
                segmentation_path = 'objects/%s/segmentation' % obj_name

                if f.exists(features_path):
                    dataset_names = f.list_datasets(features_path)
                    if dataset_names:
                        feature = pd.DataFrame()
                        for name in dataset_names:
                            dataset_path = '{group}/{dataset}'.format(
                                            group=features_path, dataset=name)
                            feature[name] = f.read(dataset_path)
                        if i == 0:
                            data[features_path] = feature
                        else:
                            data[features_path] = pd.concat(
                                [data[features_path], feature]
                            )

                if f.exists(segmentation_path):
                    dataset_names = f.list_datasets(segmentation_path)
                    for name in dataset_names:
                        dataset_path = '{group}/{dataset}'.format(
                                        group=segmentation_path, dataset=name)
                        if i == 0:
                            data[dataset_path] = f.read(dataset_path)
                        else:
                            data[dataset_path] = np.array(
                                np.append(
                                    data[dataset_path],
                                    f.read(dataset_path)
                                ),
                                dtype=data[dataset_path].dtype
                            )
                    group_names = f.list_groups(segmentation_path)
                    for g_name in group_names:
                        group_path = '{group}/{subgroup}'.format(
                                        group=segmentation_path,
                                        subgroup=g_name)
                        dataset_names = f.list_datasets(group_path)
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
                                    data[dataset_path] = np.array(
                                        np.append(
                                            data[dataset_path],
                                            f.read(dataset_path)
                                        ),
                                        dtype=data[dataset_path].dtype
                                    )

        # remove duplicate columns
        if features_path in data:
            # This could probably be done in a more optimal way
            data[features_path] = data[features_path].T.groupby(level=0).first().T

    return data


def create_object_layers(data_file):
    '''
    '''
