#! /usr/bin/env python
import mahotas as mh
from os.path import join, basename, exists
import numpy as np
import matplotlib.pylab as plt
import glob
from copy import copy
import h5py
from image_toolbox import config


def get_cycle_dir(exp_dir, cycle_number):
    exp_name = basename(exp_dir)
    return join(exp_dir, config['CYCLE_SUBDIRECTORY_NAME_FORMAT'].format(
                    experiment_name=exp_name, cycle_number=cycle_number))


def get_segmentation_dir(cycle_dir):
    return config['SEGMENTATION_FOLDER_LOCATION'].format(
                    cycle_subdirectory=cycle_dir)


def get_segmentation_filename(segmentation_dir, site_number):
    seg_filename = glob.glob(join(segmentation_dir,
                             '*_s%.4d*_segmentedCells.png' % site_number))
    if len(seg_filename) == 1:
        return seg_filename[0]
    elif len(seg_filename) > 1:
        raise Exception('There must be only one segmentation file per site.')
    else:
        raise Exception('No segmentation file found.')


def read_image(seg_filename):
    return mh.imread(seg_filename)


def get_data_filename(project_dir, site_number):
    data_dir = join(project_dir, 'data')
    data_filename = glob.glob(join(data_dir, '*_%.5d.data' % site_number))
    if len(data_filename) == 1:
        return data_filename[0]
    elif len(data_filename) > 1:
        raise Exception('There must be only one data file per site.')
    else:
        raise Exception('No data file found.')


def read_dataset(data_filename, feature_name):
    f = h5py.File(data_filename, 'r')
    feature = f[feature_name][()]
    f.close()
    return feature


def plot_data_on_image(data, im):
    feature_im = copy(im)
    objects = sorted(np.unique(im))
    objects = objects[1:]
    for obj in objects:
        feature_im[im == obj] = data[obj-1]

    plt.imshow(feature_im)
    plt.show()


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(
        description='Check Jterator dataset: plot feature values on image.')

    parser.add_argument('exp_dir', type=str,
                        help='path to experiment folder')

    parser.add_argument('-p', '--project', dest='project_name', required=True,
                        type=str,
                        help='name of the Jterator project folder')

    parser.add_argument('-c', '--cycle', dest='cycle_number', required=True,
                        type=int,
                        help='number of the sub-experiment cycle')

    parser.add_argument('-s', '--site', dest='site_number', required=True,
                        type=int,
                        help='number of image site')

    parser.add_argument('-f', '--feature', dest='feature_name',
                        action='store_true',
                        default='Cells_AreaShape_Morphology_area',
                        help='name of the feature to plot')

    args = parser.parse_args()

    if not exists(args.exp_dir):
        raise Exception('Experiment folder does not exist.')

    cycle_dir = get_cycle_dir(args.exp_dir, args.cycle_number)
    segm_dir = get_segmentation_dir(cycle_dir)
    segm_filename = get_segmentation_filename(segm_dir, args.site_number)
    im = read_image(segm_filename)

    project_dir = join(cycle_dir, args.project_name)
    data_filename = get_data_filename(project_dir, args.site_number)
    data = read_dataset(data_filename, args.feature_name)
    plot_data_on_image(data, im)
