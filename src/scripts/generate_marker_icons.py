#!/usr/bin/env python
# encoding: utf-8

import re
import numpy as np
from scipy import misc
import argparse
import os.path as p
import os

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Create marker icons for tissueMAPS')
    parser.add_argument(
        '-o', dest="output_dir",
        help='where to store the resulting files')
    parser.add_argument(
        '-i', dest='input_image', default='marker-rgb(255,255,255)-42.png',
        help='the white image to use as a source')


    args = parser.parse_args()

    if not p.exists(args.output_dir):
        os.makedirs(args.output_dir)

    colors = ['rgb(228,26,28)','rgb(55,126,184)','rgb(77,175,74)','rgb(152,78,163)','rgb(255,127,0)','rgb(255,255,51)','rgb(166,86,40)','rgb(247,129,191)','rgb(153,153,153)']

    source = misc.imread(args.input_image).astype('float32') / 255

    res = 42

    for c in colors:
        m = re.search('(\d+),(\d+),(\d+)', c)
        r, g, b = map(int, m.groups())

        mat = source.copy()
        mat[:, :, :] *= (r, g, b, 255)

        fname = p.join(
            args.output_dir,
            'marker-rgb(%d,%d,%d)-%d.png' % (r, g, b, res)
        )
        print 'Creating: ' + fname
        misc.imsave(fname, mat.astype('uint8'))















