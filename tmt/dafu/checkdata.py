#! /usr/bin/env python
import os
import numpy as np
import matplotlib.pylab as plt
from matplotlib import colors
from copy import copy
import h5py
from tmt import config
from tmt.experiment import Experiment


def read_dataset(data_filename, feature_name, site_number):
    f = h5py.File(data_filename, 'r')
    feature_loc = '/objects/cells/features'
    header = f[feature_loc].attrs.__getitem__('names')
    feature_index = np.where(header == feature_name)[0]
    id_loc = 'objects/cells/original-ids'
    header = f[id_loc].attrs.__getitem__(id_loc)
    site_id_index = np.where(header == 'ID_site')[0]
    site_ids = f[id_loc][:, site_id_index]
    cell_index = np.where(site_ids == site_number)[0]
    features = f[feature_loc][cell_index, :]
    feature = features[:, feature_index]
    f.close()
    return feature


def plot_data_on_image(data, im):
    feature_im = copy(im)
    objects = sorted(np.unique(im))
    objects = objects[1:]
    for obj in objects:
        feature_im[im == obj] = data[obj-1]

    plt.imshow(feature_im)
    plt.colorbar()
    plt.show()


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(
        description='Check Jterator dataset: plot feature values on image.')

    parser.add_argument('exp_dir', type=str, help='path to experiment folder')

    parser.add_argument('-s', '--site', dest='site_number', required=True,
                        type=int, help='number of image site')

    parser.add_argument('-f', '--feature', dest='feature_name', type=str,
                        default='Cells_AreaShape_Morphology_area',
                        help='name of the feature to plot')

    args = parser.parse_args()

    if not os.path.exists(args.exp_dir):
        raise OSError('Project folder does not exist.')

    cycles = Experiment(args.exp_dir, config).subexperiments

    images = [f.image for f in cycles[0].project.segmentation_files
              if f.site == args.site_number and f.objects == 'Cells']
    if len(images) == 1:
        im = images[0]
    elif len(images) > 1:
        raise IOError('There must be only one segmentation file per site.')
    else:
        raise IOError('No segmentation file found.')

    data_filename = os.path.join(args.exp_dir, 'data.h5')
    data = read_dataset(data_filename, args.feature_name, args.site_number)
    plot_data_on_image(data, im)
