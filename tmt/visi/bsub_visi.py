#!/usr/bin/env python
import os
from time import time
from datetime import datetime
import yaml
import glob
import argparse
import subprocess32
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
}

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Brutus submission script '
                                     'for .stk to .png conversion')

    parser.add_argument('experiment_dir', nargs='?',
                        help='path to the experiment folder')

    args = parser.parse_args()

    experiment_dir = os.path.abspath(args.experiment_dir)
    experiment = os.path.basename(experiment_dir)
    input_dir = os.path.join(experiment_dir, 'STK')

    lsf_dir = os.path.join(experiment_dir, 'lsf')
    if not os.path.exists(lsf_dir):
        print '. creating "lsf" output directory'
        os.mkdir(lsf_dir)

    # Sanity check
    check_visi_config(config)

    # Create custom config.yaml file
    config_file = os.path.join(lsf_dir, 'visi_%s.config' % experiment)
    with open(config_file, 'w') as f:
        f.write(yaml.safe_dump(config, default_flow_style=False,
                default_style='"'))

    joblist_filenames = glob.glob(os.path.join(experiment_dir, 'visi*.jobs'))
    if len(joblist_filenames) == 1:
        joblist_filename = joblist_filenames[0]
    elif len(joblist_filenames) > 1:
        raise OSError('There must not be more than one joblist file.')
    else:
        raise OSError('Joblist file does not exist.')

    with open(joblist_filename, 'r') as joblist_file:
        joblist = yaml.load(joblist_file.read())

    for job in range(1, len(joblist)+1):  # jobs are one-based!

        ts = datetime.fromtimestamp(time()).strftime('%Y-%m-%d_%H-%M-%S')
        lsf = os.path.join(experiment_dir, 'lsf',
                           'visi_%s_%.5d_%s.lsf' % (experiment, job, ts))

        print '. submitting job #%d' % job
        subprocess32.call([
             'bsub', '-W', '8:00', '-o', lsf,
             '-R', 'rusage[mem=4000,scratch=4000]',
             'visi', 'run', '--job', job,
             '--rename', '--config', config_file, input_dir
        ])
