#!/usr/bin/env python
import os
from os.path import join
import re
import h5py
from time import time
from datetime import datetime
import socket
import argparse
import yaml
from align import registration as reg
from subprocess32 import call


def on_brutus():
    hostname = socket.gethostname()
    if re.search(r'brutus', hostname):
        return True
    else:
        return False


if __name__ == '__main__':

    parser = argparse.ArgumentParser('Image registration between cycles.')

    parser.add_argument('project_dir', default=os.getcwd(),
                        help='project directory')

    parser.add_argument('--ref_cycle', dest='ref_cycle', type=int,
                        help='reference cycle')

    parser.add_argument('--ref_channel', dest='ref_channel', type=int,
                        help='reference channel')

    parser.add_argument('-b', '--batch_size', dest='batch_size', default=10,
                        type=int, help='number of jobs submitted per batch')

    args = parser.parse_args()

    project_dir = args.project_dir
    batch_size = args.batch_size

    if args.ref_channel:
        # TODO: Check that channel actually exists!
        ref_channel = args.ref_channel
    else:
        # By default use channel # 1 as reference
        ref_channel = 1

    cycle_dirs = reg.get_cycle_dirs(project_dir)

    image_filenames = reg.get_image_filenames(cycle_dirs, ref_channel)

    if args.ref_cycle:
        # TODO: Check that cycle actually exists!
        ref_cycle = args.ref_cycle - 1
    else:
        # By default use last cycle as reference
        ref_cycle = len(cycle_dirs) - 1

    # Divide list of image files into batches
    number_of_jobs = len(image_filenames[0])
    print number_of_jobs
    number_of_batches = number_of_jobs / batch_size

    for b in xrange(number_of_batches + 2):
        if b == 0:
                continue

        l = b * batch_size - batch_size
        u = b * batch_size
        if u > number_of_jobs:
                u = number_of_jobs
        batch = range(l, u)

        # Write joblist file
        registration_filenames = dict()
        for i, files in enumerate(image_filenames):
            registration_filenames['cycle%d' % i] = files[l:u]
        reference_filenames = image_filenames[ref_cycle][l:u]
        output_filename = join(project_dir, 'lsf',
                               'aligncycles_%.4d-%.4d.output' % (l+1, u+1))
        joblist = yaml.dump({
                    'registration': registration_filenames,
                    'reference': reference_filenames,
                    'output': output_filename
                  }, default_flow_style=False)
        joblist_filename = 'aligncycles_%.4d-%.4d.joblist' % (l+1, u+1)
        joblist_filename = join(project_dir, 'lsf', joblist_filename)
        with open(joblist_filename, 'w') as outfile:
            outfile.write(joblist)

        # Create output file
        h5py.File(output_filename, 'w')

        # Make timestamp
        ts = time()
        st = datetime.fromtimestamp(ts).strftime('%Y-%m-%d_%H-%M-%S')
        lsf = os.path.join(project_dir, 'lsf', 'visi_%.5d_%d-%d_%s.lsf' %
                           (b, l, u, st))

        # Submit job
        call(['bsub', '-W', '8:00', '-o', lsf,
             '-R', 'rusage[mem=4000,scratch=4000]',
             'align', joblist_filename])
