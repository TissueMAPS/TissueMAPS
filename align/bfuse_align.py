#!/usr/bin/env python
import os
from os.path import join, exists
import json
import h5py
import argparse
from glob import glob
from align import registration as reg
from image_toolbox import config
from image_toolbox.util import load_config, check_config
from image_toolbox.project import Project
from image_toolbox.experiment import Experiment


def combine_outputs(output_files, cycle_names):
    descriptor = list()
    for i, key in enumerate(cycle_names):
        descriptor[i] = dict()
        descriptor[i]['xShift'] = []
        descriptor[i]['yShift'] = []
        descriptor[i]['fileName'] = []
    # Combine output from different output files
    for output in output_files:
        f = h5py.File(output, 'r')
        for i, key in enumerate(cycle_names):
            descriptor[i]['fileName'].extend(f[key]['reg_file'][()])
            descriptor[i]['xShift'].extend(f[key]['x_shift'][()])
            descriptor[i]['yShift'].extend(f[key]['y_shift'][()])
        f.close()
    return descriptor


def calc_global_overlap(descriptor):
    top_overlap = []
    bottom_overlap = []
    right_overlap = []
    left_overlap = []
    number_of_sites = len(descriptor[0]['xShift'])
    print '. number of sites: %d' % number_of_sites
    for site in xrange(number_of_sites):
        x_shift = [c['xShift'][site] for c in descriptor.values()]
        y_shift = [c['yShift'][site] for c in descriptor.values()]
        (top, bottom, right, left) = reg.calculate_overlap(x_shift, y_shift)
        top_overlap.append(top)
        bottom_overlap.append(bottom)
        right_overlap.append(right)
        left_overlap.append(left)

    # Calculate total overlap across all sites
    top_overlap = max(map(abs, top_overlap))
    bottom_overlap = max(map(abs, bottom_overlap))
    right_overlap = max(map(abs, right_overlap))
    left_overlap = max(map(abs, left_overlap))

    return (top_overlap, bottom_overlap, right_overlap, left_overlap)


if __name__ == '__main__':

    parser = argparse.ArgumentParser('Fuse jobs for the calculation of \
                                     shift between images \
                                     of different acquisition cycles.')

    parser.add_argument('experiment_dir', default=os.getcwd(),
                        help='experiment directory')

    parser.add_argument('--ref_cycle', dest='ref_cycle',
                        type=int, help='reference cycle number \
                        (defaults to number of last cycle)')

    parser.add_argument('--segm_dir', dest='segm_dir',
                        type=str, help='relative path to segmentation directory \
                        (relative from other cycle subdirectory)')

    parser.add_argument('--segm_trunk', dest='segm_trunk',
                        type=str, help='trunk of segmentation filenames \
                        (the substring all image filenames have in common)')

    parser.add_argument('-m', '--max_shift', dest='max_shift',
                        type=int, default=100,
                        help='maximally tolerated shift in pixels \
                        (defaults to 100)')

    parser.add_argument('-c', '--config', dest='config',
                        help='use custom yaml configuration file \
                        (defaults to "image_toolbox" configuration)')

    args = parser.parse_args()

    experiment_dir = args.experiment_dir
    max_shift = args.max_shift

    if args.config:
        # Overwrite default "image_toolbox" configuration
        print '. get configuration from file: %s' % args.config
        config = load_config(args.config)
        check_config(config)

    experiment = Experiment(experiment_dir, config)
    cycles = experiment.subexperiments

    if args.ref_cycle:
        ref_cycle = args.ref_cycle
    else:
        # By default use last cycle as reference
        ref_cycle = len(cycles)

    print '. reference cycle: %d' % ref_cycle
    ref_cycle_name = [c.name for c in cycles if c.cycle == ref_cycle][0]

    if args.segm_dir:
        segm_dir = args.segm_dir
    else:
        project = Project(experiment_dir, config, subexperiment=ref_cycle_name)
        # default for Jterator projects
        segm_dir = join('..', '..', project.segmentation_dir)

    print '. define segmentation directory: %s' % segm_dir

    if args.segm_trunk:
        segm_trunk = args.segm_trunk
    else:
        exp_name = [c.experiment for c in cycles
                    if c.name == ref_cycle_name][0]
        segm_trunk = config['SUBEXPERIMENT_FILE_FORMAT'].format(
                                                        experiment=exp_name,
                                                        cycle=ref_cycle)

    print '. define segmentation trunk: %s' % segm_trunk

    # Get calculate shifts from output files
    output_dir = join(experiment_dir, 'lsf', 'registration')
    print '. load shift calculations from %s' % output_dir


    output_files = glob(join(output_dir, '*.output'))
    # Preallocate final output
    f = h5py.File(output_files[0], 'r')
    cycle_names = f.keys()
    f.close()

    descriptor = combine_outputs(output_dir, cycle_names)

    # Calculate overlap at each site
    print '. calculate overlap between sites'
    top_ol, bottom_ol, right_ol, left_ol = calc_global_overlap(descriptor)

    # Limit total overlap by maximally tolerated shift
    if top_ol > max_shift:
        top_ol = max_shift
    if bottom_ol > max_shift:
        bottom_ol = max_shift
    if right_ol > max_shift:
        right_ol = max_shift
    if left_ol > max_shift:
        left_ol = max_shift

    # Determine indices of sites where shift exceeds maximally tolerated shift
    # in either direction
    index = []
    for cycle in cycle_names:
        index.extend([descriptor[cycle]['xShift'].index(s)
                     for s in descriptor[cycle]['xShift']
                     if abs(s) > max_shift])
        index.extend([descriptor[cycle]['yShift'].index(s)
                     for s in descriptor[cycle]['yShift']
                     if abs(s) > max_shift])

    no_shift_index = number_of_sites * [0]
    for i in index:
        no_shift_index[i] = 1
    no_shift_count = len(index)

    # Write shiftDescriptor.json files
    for i, cycle_name in enumerate(cycle_names):
        current_cycle = [c for c in cycles if c.name == cycle_name][0]
        aligncycles_dir = current_cycle.project.shift_dir
        if not exists(aligncycles_dir):
            os.mkdir(aligncycles_dir)
        descriptor_filename = current_cycle.project.shift_file
        print '. create shift descriptor file: %s' % descriptor_filename

        descriptor[i]['lowerOverlap'] = bottom_ol
        descriptor[i]['upperOverlap'] = top_ol
        descriptor[i]['rightOverlap'] = right_ol
        descriptor[i]['leftOverlap'] = left_ol
        descriptor[i]['maxShift'] = max_shift
        descriptor[i]['noShiftIndex'] = no_shift_index
        descriptor[i]['noShiftCount'] = no_shift_count
        descriptor[i]['SegmentationDirectory'] = segm_dir
        descriptor[i]['SegmentationFileNameTrunk'] = segm_trunk
        descriptor[i]['cycleNum'] = current_cycle.cycle

        with open(descriptor_filename, 'w') as outfile:
            outfile.write(json.dumps(descriptor[i],
                          indent=4, sort_keys=True, separators=(',', ': ')))
