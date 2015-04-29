#!/usr/bin/env python
import os
from os.path import (join, exists, basename)
import re
import h5py
import argparse
from glob import glob
from align import registration as reg


if __name__ == '__main__':

    parser = argparse.ArgumentParser('Fuse jobs for the calculation of \
                                     shift between images \
                                     of different acquisition cycles.')

    parser.add_argument('project_dir', default=os.getcwd(),
                        help='project directory')

    parser.add_argument('--ref_cycle', dest='ref_cycle', type=int,
                        help='reference cycle number \
                        (refers to cycle with segmentation files)')

    parser.add_argument('--segmentation_dir', dest='segmentation_dir', type=str,
                        help='relative path to segmentation directory \
                        (relative from other cycle subdirectory)')

    parser.add_argument('--segmentation_trunk', dest='segmentation_dir', type=str,
                        help='trunk of segmentation filenames \
                        (the substring all image filenames have in common)')

    args = parser.parse_args()

    project_dir = args.project_dir

    print '. get cycle directories'
    cycle_dirs = reg.get_cycle_dirs(project_dir)

    aligncycles_dirs = [join(d, 'ALIGNCYCLES') for d in cycle_dirs]
    for output_dir in aligncycles_dirs:
        if not exists(output_dir):
            print '. create output directory: %s' % output_dir
            os.mkdir(output_dir)

    if args.ref_cycle:
        ref_cycle = args.ref_cycle - 1
    else:
        # By default use last cycle as reference
        ref_cycle = len(cycle_dirs) - 1

    if args.segmentation_dir:
        segmentation_dir = args.segmentation_dir
    else:
        segmentation_dir = join('..', cycle_dirs[ref_cycle], 'SEGMENTATION')
        print '. define segmentation directory: %s' % segmentation_dir

    if args.segmentation_trunk:
        segmentation_trunk = args.segmentation_trunk
    else:
        example_filename = glob(join(cycle_dirs[ref_cycle], 'TIFF', '*.png'))[0]
        r = re.compile(r'([^_]+)_.*')  # TODO: this can be improved!
        segmentation_trunk = re.search(r, basename(example_filename))[1]

    # Get calculate shifts from output files
    output_files = glob(join(project_dir, 'lsf', 'registration', '*.output'))
    descriptor = dict()
    # Preallocate final output
    f = h5py.File(output_files[0], 'r')
    cycles = f.keys()
    f.close()
    for cycle in cycles:
        descriptor[cycle] = dict()
        descriptor[cycle]['x_shift'] = []
        descriptor[cycle]['y_shift'] = []
        descriptor[cycle]['reg_file'] = []
    # Combine output from different output files
    for output in output_files:
        f = h5py.File(output, 'r')
        for cycle in f.keys():
            descriptor[cycle]['x_shift'].append(cycle['x_shift'])
            descriptor[cycle]['y_shift'].append(cycle['y_shift'])
            descriptor[cycle]['reg_file'].append(cycle['reg_file'])
        f.close()

    # Calculate max shift in x and y direction for overlap



