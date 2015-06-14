#! /usr/bin/env python
# encoding: utf-8

from os.path import isdir, join, basename, dirname
from os import listdir
import numpy as np
import h5py
import yaml
import glob
import re
from copy import copy
from image_toolbox import config
from datafusion import config as df_config
from image_toolbox.image import Image
from image_toolbox.experiment import Experiment
from image_toolbox.util import load_config


'''
Script for fusing measurement data generated by Jterator for use with TissueMAPS.

Jterator generates an HDF5 file for each job. Here we load all files for a
particular experiment (potentially consisting of different sub-experiments,
i.e. cycles) and merge their content into a single HDF5 file.
'''

header_mapper = df_config['CHANNEL_MAPPER']

names = list()
count = 0
for i, cycle in header_mapper.iteritems():
    if isinstance(cycle, dict):
        for old, new in cycle.iteritems():
            count += 1
            names.append(new)

if len(np.unique(names)) < count:
    raise Exception('Names have to be unique.')


def get_jtproject_names(cycle_dir):
    '''
    Get name of a Jterator project, i.e. a sub-folder in the experiment
    directory that contains a .pipe file.
    '''
    return [f for f in listdir(cycle_dir)
            if isdir(join(cycle_dir, f))
            and glob.glob(join(cycle_dir, f, '*.pipe'))]


def image_name_from_joblist(joblist, data_filename):
    job_id = int(re.search(r'_(\d+).data$', data_filename).group(1).lstrip('0'))
    return joblist[job_id].values()[0]


def rename_features(feature_names, mapper):
    '''
    Rename feature, i.e. replace substring in a feature name by another
    as defined in a 'mapper' dictionary.

    Parameters:
        :feature_names:     List of strings.
        :mapper:            Dictionary. keys - old names, values - new names.

    Returns:
        renamed features (list of strings)
    '''
    for i, feature in enumerate(feature_names):
        for j, substring in enumerate(mapper.keys()):
            r = re.compile(substring)
            match = re.search(r, feature)
            if match:
                feature_names[i] = re.sub(mapper.keys()[j],
                                          mapper.values()[j],
                                          feature_names[i])
    return feature_names


def get_data_files(project_dir):
    '''
    List all data HDF5 files for a given Jterator project.
    '''
    return sorted(glob.glob(join(project_dir, 'data', '*.data')))


def merge_data(data_files, names, as_int=False):
    '''
    Merge Jterator data of one experiment cycle stored in several HDF5 files.

    Parameters:
    :data_files:        Paths to Jterator data files : list.
    :names:             Names of a dataset in a HDF5 file : list.
    :as_int:            Convert to integer datatype : bool?

    :returns:           Dataset of shape nxp,
                        where n is the number of objects
                        and p the number of features : ndarray.
    '''
    joblist_filename = glob.glob(join(dirname(data_files[0]), '..',
                                 '*.jobs'))[0]
    joblist = yaml.load(open(joblist_filename).read())
    ids = list()
    feature_names = list()
    for job_ix, filename in enumerate(data_files):

        f = h5py.File(filename, 'r')
        if not f.keys():
            raise Exception('File "%s" is empty' % filename)

        for feat_ix, name in enumerate(names):

            if name not in f.keys():
                raise Exception('Dataset "%s" does not exist in file "%s'
                                % (name, filename))
            ids = re.search(r'.*ObjectIds.*', name, re.IGNORECASE)
            if ids:
                # Get positional information from filename
                im_file = image_name_from_joblist(joblist, filename)
                image = Image(im_file, config)
                (row, column) = image.coordinates  # returns 0-based indices
                site = image.site
                # Translate site specific ids to global ids
                nitems = len(f.values()[0])
                feat = np.vstack((np.repeat(site, nitems),
                                 np.repeat(row, nitems),
                                 np.repeat(column, nitems),
                                 f[ids.group(0)][:nitems]))
                name = ['ID_site', 'ID_row', 'ID_column', 'ID_object']
            else:
                feat = f[name][()]
                name = [name]
            feat = np.matrix(feat)
            if feat.shape[0] < feat.shape[1]:
                feat = feat.H
            if feat_ix == 0:
                feature = feat
            else:
                feature = np.hstack((feature, feat))
            if job_ix == 0:
                feature_names += name

        f.close()

        if job_ix == 0:
            features = feature
        else:
            features = np.vstack((features, feature))

    feature_names = np.array(feature_names, dtype=np.string_)

    if as_int:
        return (features.astype(int), feature_names)
    else:
        return (features, feature_names)


def build_global_ids(ids, id_names):
    '''
    Build global, continuous ids from local (image specific) ids in combination
    with row and column ids (position of the image in the acquisition "snake").

    Parameters:
    :ids:               numpy matrix with dimensions nx3, where n is the number
                        of objects
    :id_names:          numpy array of strings specifying the 3 ids:
                        "ID_row", "ID_column", "ID_object"

    Returns:
        numpy array with dimensions 1xn
    '''
    global_ids = list()
    ix_row = np.where(id_names == 'ID_row')[0]
    ix_col = np.where(id_names == 'ID_column')[0]
    ix_local = np.where(id_names == 'ID_object')[0]
    # avoid 'matrix' !!!
    rows = np.squeeze(np.asarray(ids[:, ix_row]))
    columns = np.squeeze(np.asarray(ids[:, ix_col]))
    n_row = np.max(ids[:, ix_row])
    n_col = np.max(ids[:, ix_col])
    global_ids = np.squeeze(np.asarray(ids[:, ix_local])).copy()

    offset = 0
    for r in range(1, n_row+1):
        for c in range(1, n_col+1):
            # Get the indices of the rows that belong to the site with row r
            # and column c
            ix = np.where(np.logical_and(rows == r, columns == c))[0]
            local_ids = np.squeeze(np.asarray(ids[ix, ix_local]))
            # Add a constant to the local ids and save them in the vector
            # global_ids
            global_ids[ix] = local_ids + offset
            offset = np.max(local_ids + offset)

    return global_ids


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(
        description='Merge data generated by Jterator for use in tissueMAPS.')

    parser.add_argument('experiment_dir', nargs='*',
                        help='absolute path to experiment directory')

    parser.add_argument('-o', '--output', dest='output_dir', required=True,
                        help='directory where the HDF5 file should be saved')

    parser.add_argument('-c', '--config', dest='config',
                        help='path to custom yaml configuration file \
                        (defaults to "datafusion" configuration)')

    args = parser.parse_args()

    if args.config:
        # Overwrite default "datafusion" configuration
        df_config = load_config(args.config)

    exp_dir = args.experiment_dir[0]
    output_dir = args.output_dir

    segmentation_project_dir = join(exp_dir,
                                    df_config['SEGMENTATION_PROJECT'].format(
                                            experiment=basename(exp_dir)))

    if not exp_dir:
        raise Exception('Project directory "%s" does not exist.'
                        % exp_dir)

    if not output_dir:
        raise Exception('Output directory "%s" does not exist.' % output_dir)

    output_filename = join(output_dir, 'data.h5')

    cycles = Experiment(exp_dir, config).subexperiments

    data_header = np.array(list(), dtype=np.string_)
    for i, c in enumerate(cycles):

        print('. Extracting features of cycle #%d: %s' %
              (c.cycle, c.name))

        cycle_dir = join(exp_dir, c.name)
        project_names = get_jtproject_names(cycle_dir)

        for project_name in project_names:

            project_dir = join(cycle_dir, project_name)

            if project_dir == segmentation_project_dir:
                # data of segmentation project is handled separately
                continue

            print '.. Merging data of Jterator project "%s"' % project_name

            data_files = get_data_files(project_dir)

            f = h5py.File(data_files[0], 'r')
            feature_names = f.keys()
            f.close()

            if 'OriginalObjectIds' not in feature_names:
                raise Exception('Files must contain a dataset called "%s"' %
                                'OriginalObjectIds')

            (features, feature_names) = merge_data(data_files,
                                                   names=feature_names)

            if features.shape[1] != len(feature_names):
                raise Exception('Number of features in dataset and length of '
                                'list with feature names must be identical.')

            if i == 0:
                data = features
            else:
                data = np.hstack((data, features))

            feature_names = rename_features(feature_names,
                                            header_mapper[c.cycle])
            # # convert to safe string format for HDF5
            # feature_names = np.array(map(np.string_, feature_names))
            data_header = np.hstack((data_header, feature_names))

    print '. Combining data from different cycles'
    (data_header, unique_ix) = np.unique(data_header, return_index=True)
    # TODO: sanity checks
    data = data[:, unique_ix]

    # separate object ids from dataset
    print '. Building global object ids'
    ids_ix = np.where(np.array([re.search('ID', i) is not None
                                for i in data_header]))[0]
    ids = data[:, ids_ix].astype(int)
    ids_header = data_header[ids_ix]
    data = np.delete(data, ids_ix, axis=1)
    data_header = np.delete(data_header, ids_ix)
    global_ids = build_global_ids(ids, ids_header)

    print '. Separate features belonging to different objects'
    objects = [re.match(r'^([^_]+)', name).group(1) for name in data_header]
    (objects, object_ix) = np.unique(objects, return_inverse=True)

    print '. Writing fused data into HDF5 file "%s"' % output_filename
    f = h5py.File(output_filename, 'w')  # truncate file if exists
    f.create_dataset('parent', data=np.string_('cells'))  # hard-coded for now
    for i, obj in enumerate(objects):

        print '. Writing data for object "%s"' % obj

        obj_ix = object_ix == i
        obj_name = obj.lower()  # use lower case consistently

        location = 'objects/%s/original-ids' % obj_name
        f.create_dataset(location, data=ids)
        f[location].attrs.__setitem__('names', ids_header)

        f.create_dataset('objects/%s/ids' % obj_name, data=global_ids)

        # data_files = get_data_files(segmentation_project_dir)

        # centroids = merge_data(data_files, names=['%s_Centroids' % obj])
        # # TODO: centroids have to be global!!! 
        # # illuminati.segment.compute_cell_centroids()
        # location = 'objects/%s/centroids' % obj_name
        # f.create_dataset(location, data=centroids)
        # f[location].attrs.__setitem__('names', np.array(['y', 'x']))

        # border = merge_data(data_files, names=['%s_BorderIx' % obj],
        #                     as_int=True)
        # f.create_dataset('objects/%s/border' % obj_name, data=border)

        location = 'objects/%s/features' % obj_name
        f.create_dataset(location, data=data[:, obj_ix])
        # Add the 'data_header' as an attribute
        f[location].attrs.__setitem__('names', data_header[obj_ix])

    f.close()
