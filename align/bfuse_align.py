#!/usr/bin/env python
import os
from os.path import join, exists
import re
import json
import h5py
import argparse
from glob import glob
from align import registration as reg
from illuminati import util


if __name__ == '__main__':

    parser = argparse.ArgumentParser('Fuse jobs for the calculation of \
                                     shift between images \
                                     of different acquisition cycles.')

    parser.add_argument('project_dir', default=os.getcwd(),
                        help='project directory')

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
                        default=os.path.join(os.path.dirname(__file__), '..',
                                             'config.yaml'),
                        help='use custom yaml configuration file \
                        (defaults to config.yaml form "image_toolbox")')

    args = parser.parse_args()

    project_dir = args.project_dir
    max_shift = args.max_shift

    config_filename = args.config
    print '. get configuration from config file: %s' % config_filename
    config = util.load_config(config_filename)
    util.check_config(config)

    # Initialize utility object with configuration settings
    project = util.Project(config)
    cycles = util.Cycles(config)

    print '. get cycle directories'
    cycle_dirs = cycles.get_cycle_directories(project_dir)

    if args.ref_cycle:
        ref_cycle = args.ref_cycle
    else:
        # By default use last cycle as reference
        ref_cycle = len(cycle_dirs)

    print '. reference cycle: %d' % ref_cycle
    reference_cycle = [c for c in cycle_dirs if c.cycle_number == ref_cycle][0]

    if args.segm_dir:
        segm_dir = args.segm_dir
    else:
        segm_dir = join('..', project.get_segmentation_dir(project_dir,
                        reference_cycle))

    print '. define segmentation directory: %s' % segm_dir

    if args.segm_trunk:
        segm_trunk = args.segm_trunk
    else:
        example_filename = project.get_image_files(project_dir,
                                                   reference_cycle)[0]
        exp_name = project.get_expname_from_filename(example_filename)
        # This can be done nicer
        segm_trunk = re.sub(r'{experiment_name}', exp_name,
                            config['FILENAME_FORMAT'])
        segm_trunk = re.sub(r'{cycle_number}', str(ref_cycle), segm_trunk)

    print '. define segmentation trunk: %s' % segm_trunk

    # Get calculate shifts from output files
    output_dir = join(project_dir, 'lsf', 'registration')
    print '. load shift calculations from %s' % output_dir
    output_files = glob(join(output_dir, '*.output'))
    descriptor = dict()
    # Preallocate final output
    f = h5py.File(output_files[0], 'r')
    cycles_names = f.keys()
    f.close()
    for cycle in cycles_names:
        descriptor[cycle] = dict()
        descriptor[cycle]['xShift'] = []
        descriptor[cycle]['yShift'] = []
        descriptor[cycle]['fileName'] = []
    # Combine output from different output files
    for output in output_files:
        f = h5py.File(output, 'r')
        for cycle in cycles_names:
            descriptor[cycle]['fileName'].extend(f[cycle]['reg_file'][()])
            descriptor[cycle]['xShift'].extend(f[cycle]['x_shift'][()])
            descriptor[cycle]['yShift'].extend(f[cycle]['y_shift'][()])
        f.close()

    # Calculate overlap at each site
    print '. calculate overlap between sites'
    top_overlap = []
    bottom_overlap = []
    right_overlap = []
    left_overlap = []
    number_of_sites = len(descriptor[cycles_names[0]]['xShift'])
    print '. number of sites: %d' % number_of_sites
    for site in xrange(number_of_sites):
        x_shift = [c['xShift'][site] for c in descriptor.values()]
        y_shift = [c['yShift'][site] for c in descriptor.values()]
        (top, bottom, right, left) = reg.calculate_overlap(x_shift, y_shift)
        top_overlap.append(top)
        bottom_overlap.append(bottom)
        right_overlap.append(right)
        left_overlap.append(left)

    # Get total overlap across all sites
    total_top_overlap = max(map(abs, top_overlap))
    total_bottom_overlap = max(map(abs, bottom_overlap))
    total_right_overlap = max(map(abs, right_overlap))
    total_left_overlap = max(map(abs, left_overlap))

    # Limit total overlap by maximally tolerated shift
    if total_top_overlap > max_shift:
        total_top_overlap = max_shift
    if total_bottom_overlap > max_shift:
        total_bottom_overlap = max_shift
    if total_right_overlap > max_shift:
        total_right_overlap = max_shift
    if total_left_overlap > max_shift:
        total_left_overlap = max_shift

    # Get indices of sites where shift exceeds maximally tolerated shift
    # in either direction
    index = []
    for cycle in cycles_names:
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
    for cycle_object in cycle_dirs:
        aligncycles_dir = cycles.get_shift_dir(project_dir, cycle_object)
        if not exists(aligncycles_dir):
            os.mkdir(aligncycles_dir)
        descriptor_filename = join(aligncycles_dir, 'shiftDescriptor.json')
        print '. create shift descriptor file: %s' % descriptor_filename

        cycle_num = cycle_object.cycle_number
        cycle = 'cycle%d' % cycle_num
        descriptor[cycle]['lowerOverlap'] = total_bottom_overlap
        descriptor[cycle]['upperOverlap'] = total_top_overlap
        descriptor[cycle]['rightOverlap'] = total_right_overlap
        descriptor[cycle]['leftOverlap'] = total_left_overlap
        descriptor[cycle]['maxShift'] = max_shift
        descriptor[cycle]['noShiftIndex'] = no_shift_index
        descriptor[cycle]['noShiftCount'] = no_shift_count
        descriptor[cycle]['SegmentationDirectory'] = segm_dir
        descriptor[cycle]['SegmentationFileNameTrunk'] = segm_trunk
        descriptor[cycle]['cycleNum'] = cycle_num

        with open(descriptor_filename, 'w') as outfile:
            outfile.write(json.dumps(descriptor[cycle],
                          indent=4, sort_keys=True, separators=(',', ': ')))
