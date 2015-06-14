#!/usr/bin/env python
import os
from os.path import (join, exists)
import re
from time import time
from datetime import datetime
import socket
import argparse
import yaml
from natsort import natsorted
from subprocess32 import call
from illuminati.util import Project, Experiment
from image_toolbox import config
from image_toolbox.util import load_config, check_config


def on_brutus():
    hostname = socket.gethostname()
    if re.search(r'brutus', hostname):
        return True
    else:
        return False


if __name__ == '__main__':

    parser = argparse.ArgumentParser('Submit jobs for calculating the shift ' 
                                     'between images of different acquisition cycles.')

    parser.add_argument('experiment_dir', default=os.getcwd(),
                        help='experiment directory')

    parser.add_argument('--ref_cycle', dest='ref_cycle', type=int,
                        help='reference cycle number \
                        (defaults to number of last cycle)')

    parser.add_argument('--ref_channel', dest='ref_channel', default=1,
                        type=int, help='reference channel number \
                        (defaults to 1)')

    parser.add_argument('-b', '--batch_size', dest='batch_size', default=5,
                        type=int, help='number of jobs submitted per batch \
                        (defaults to 5)')

    parser.add_argument('-c', '--config', dest='config',
                        help='use custom yaml configuration file \
                        (defaults to "image_toolbox" config file)')

    args = parser.parse_args()

    experiment_dir = args.experiment_dir
    batch_size = args.batch_size

    if args.config:
        # Overwrite default "image_toolbox" configuration
        print '. get configuration from file: %s' % args.config
        config = load_config(args.config)
        check_config(config)

    cycles = Experiment(experiment_dir, config).subexperiments

    print '. found %d cycles' % len(cycles)

    ref_channel = args.ref_channel
    print '. reference channel: %d' % ref_channel

    print '. get image filenames of reference channel'
    image_filenames = []
    for c in cycles:
        project = Project(experiment_dir, config, subexperiment=c.name)
        files = [f.filename for f in project.image_files
                 if f.channel == ref_channel]  # only from reference channel
        files = natsorted(files)  # ensure correct order
        image_filenames.append(files)

    number_of_sites = len(image_filenames[0])
    print '. number of sites: %d' % number_of_sites

    if args.ref_cycle:
        ref_cycle = args.ref_cycle - 1  # for zero-based indexing!
    else:
        # By default use last cycle as reference
        ref_cycle = len(cycles) - 1  # for zero-based indexing!

    print '. reference cycle: %d' % (ref_cycle + 1)

    # Divide list of image files into batches
    number_of_batches = number_of_sites / batch_size
    print '. batch-size: %d' % batch_size
    print '. number of batches: %d' % number_of_batches

    output_dir = join(experiment_dir, 'lsf')
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
        if u > number_of_sites:
                u = number_of_sites
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

        # Make timestamp
        ts = time()
        st = datetime.fromtimestamp(ts).strftime('%Y-%m-%d_%H-%M-%S')
        lsf = os.path.join(experiment_dir, 'lsf', 'align_%.5d_%d-%d_%s.lsf' %
                           (b, l, u, st))

        # Submit job
        call(['bsub', '-W', '8:00', '-o', lsf,
             '-R', 'rusage[mem=4000,scratch=4000]',
             'align', joblist_filename])
