#!/usr/bin/env python
import os
from os.path import (join, exists)
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
                        help='reference cycle number')

    parser.add_argument('--ref_channel', dest='ref_channel', default=1,
                        type=int, help='reference channel number')

    parser.add_argument('-b', '--batch_size', dest='batch_size', default=5,
                        type=int, help='number of jobs submitted per batch')

    args = parser.parse_args()

    project_dir = args.project_dir
    batch_size = args.batch_size
    ref_channel = args.ref_channel

    print '. get cycle directories'
    cycle_dirs = reg.get_cycle_dirs(project_dir)

    print '. get image filenames'
    image_filenames = reg.get_image_filenames(cycle_dirs, ref_channel)

    if args.ref_cycle:
        ref_cycle = args.ref_cycle - 1
    else:
        # By default use last cycle as reference
        ref_cycle = len(cycle_dirs) - 1

    print '. reference channel: %d' % ref_channel
    print '. reference cycle: %d' % ref_cycle

    # Divide list of image files into batches
    number_of_jobs = len(image_filenames[0])
    print '. number of jobs: %d' % number_of_jobs
    number_of_batches = number_of_jobs / batch_size
    print '. batch-size: %d' % batch_size
    print '. number of batches: %d' % number_of_batches

    output_dir = join(project_dir, 'lsf')
    if not exists(output_dir):
        print '. create output directory: %s' % output_dir
        os.mkdir(output_dir)

    registration_dir = join(output_dir, 'registration')
    if not exists(registration_dir):
        print '. create output subdirectory for registration: %s' % registration_dir
        os.mkdir(registration_dir)

    joblists_dir = join(output_dir, 'joblists')
    if not exists(joblists_dir):
        print '. create output subdirectory for joblists: %s' % joblists_dir
        os.mkdir(joblists_dir)

    for b in xrange(number_of_batches + 2):
        if b == 0:
                continue

        print '\n. process batch # %d:' % b

        l = b * batch_size - batch_size
        u = b * batch_size
        if u > number_of_jobs:
                u = number_of_jobs
        batch = range(l, u)

        # Write joblist file
        print '.. create joblist'
        registration_filenames = dict()
        for i, files in enumerate(image_filenames):
            registration_filenames['cycle%d' % (i+1)] = files[l:u]
        reference_filenames = image_filenames[ref_cycle][l:u]
        output_filename = join(registration_dir,
                               'align_%.4d-%.4d.output' % (l+1, u))
        joblist = yaml.dump({
                    'registration': registration_filenames,
                    'reference': reference_filenames,
                    'output': output_filename
                  }, default_flow_style=False)
        joblist_filename = join(joblists_dir,
                                'align_%.4d-%.4d.joblist' % (l+1, u))
        print '.. write joblist to file: %s' % joblist_filename
        with open(joblist_filename, 'w') as outfile:
            outfile.write(joblist)

        # Create output file
        print '.. create output file: %s' % output_filename
        h5py.File(output_filename, 'w')

        # Make timestamp
        ts = time()
        st = datetime.fromtimestamp(ts).strftime('%Y-%m-%d_%H-%M-%S')
        lsf = os.path.join(project_dir, 'lsf', 'align_%.5d_%d-%d_%s.lsf' %
                           (b, l, u, st))

        # Submit job
        call(['bsub', '-W', '8:00', '-o', lsf,
             '-R', 'rusage[mem=4000,scratch=4000]',
             'align', joblist_filename])
