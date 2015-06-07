#!/usr/bin/env python
import os
import os.path as osp
from time import time
from datetime import datetime
import yaml
import glob
import argparse
from subprocess32 import call, check_call
from visi.util import check_visi_config


'''
Brutus submission script for stk to png conversion.

Automatically generates a custom config file and joblist files.

'''

# This could be written directly in YAML
config = {
    'FILENAME_FORMAT': '{project}_s{site:0>4}_r{row:0>2}_c{column:0>2}_{filter}_C{channel:0>2}.png',
    'ACQUISITION_MODE': 'ZigZagHorizontal',
    'ACQUISITION_LAYOUT': 'columns>rows',
    'OUTPUT_DIRECTORY_NAME': 'TIFF'
}

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Brutus submission script '
                                     'for .stk to .png image conversion')

    parser.add_argument('project_dir', nargs='?',
                        help='path to the project folder')

    parser.add_argument('-b', '--batch_size', dest='batch_size',
                        type=int, default=20,
                        help='number of "jobs" that are submitted per batch \
                              default: 20')

    args = parser.parse_args()

    project_dir = osp.abspath(args.project_dir)
    input_dir = osp.join(project_dir, 'STK')
    batch_size = args.batch_size

    lsf_dir = osp.join(project_dir, 'lsf')
    if not osp.exists(lsf_dir):
        print '. creating "lsf" output directory'
        os.mkdir(lsf_dir)

    # Sanity check
    check_visi_config(config)

    # Create custom config.yaml file
    config_file = osp.join(lsf_dir, 'visi_custom.config')
    with open(config_file, 'w') as f:
        # Write it in safe mode
        f.write(yaml.safe_dump(config, default_flow_style=False,
                default_style='"'))

    print '. creating joblist files'
    joblists_dir = osp.join(lsf_dir, 'joblists')
    if not osp.exists(joblists_dir):
        os.mkdir(joblists_dir)
    command = ['visi', '-o', joblists_dir, '--joblist', input_dir]
    check_call(command)

    joblist_files = glob.glob(osp.join(joblists_dir, '*.joblist'))

    if not joblist_files:
        raise Exception('Could not find any .joblist files.')

    for joblist_file in joblist_files:

        print '. processing joblist from file "%s"' % joblist_file

        subproject_name = osp.splitext(osp.basename(joblist_file))[0]
        wildcards = '%s*' % subproject_name

        joblist_content = yaml.load(open(joblist_file).read())

        jobs = map(int, joblist_content.keys())
        number_of_jobs = len(joblist_content)
        number_of_batches = number_of_jobs / batch_size

        for i in xrange(number_of_batches):

            batch = i + 1  # one-based
            lower = batch * batch_size - batch_size
            upper = batch * batch_size - 1
            if upper > number_of_jobs:
                upper = number_of_jobs - 1
            batch_range = '%s-%s' % (jobs[lower], jobs[upper])

            ts = time()
            st = datetime.fromtimestamp(ts).strftime('%Y-%m-%d_%H-%M-%S')
            lsf = osp.join(project_dir, 'lsf', 'visi_%s_%.5d_%s_%s.lsf'
                           % (subproject_name, batch, batch_range, st))

            print '. submitting job %d: %s' % (batch, batch_range)
            call([
                 'bsub', '-W', '8:00', '-o', lsf,
                 '-R', 'rusage[mem=4000,scratch=4000]',
                 'visi', '--rename', '--split_output',
                 '--batch', '%s' % batch_range,
                 '--config', config_file,
                 input_dir, '--wildcards', wildcards
            ])
