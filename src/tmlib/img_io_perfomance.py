#!/usr/bin/env python
import os
import re
import glob
import tempfile
import cv2
import png
import time
import numpy as np
# from gi.repository import Vips
import h5py


def write_images_to_files(images, image_files):
    for i, f in enumerate(image_files):
        img = images[i]
        cv2.imwrite(f, img)


def read_images_from_files(image_files):
    for f in image_files:
        img = cv2.imread(f, cv2.IMREAD_UNCHANGED)


def write_images_to_hdf5_file(data_file, images, **kwargs):
    stream = h5py.File(data_file, 'w')
    for f, img in images.iteritems():
        if 'compression_filter' in kwargs:
            stream.create_dataset(os.path.basename(f), data=img,
                                  compression=kwargs['compression_filter'])
        else:
            stream.create_dataset(os.path.basename(f), data=img)
    stream.close()


def read_images_from_hdf5_file(data_file, image_files):
    stream = h5py.File(data_file, 'r')
    for f in image_files:
        img = stream[os.path.basename(f)][()]
    stream.close()


if __name__ == '__main__':

    image_dir = '/Users/mdh/testdata/150820-Testset-CV/150820-Testset-CV-1/images'
    image_files = glob.glob(os.path.join(image_dir, '*_2.png'))

    data_file = os.path.join(tempfile.gettempdir(), 'images.h5')

    images = {f: cv2.imread(f, cv2.IMREAD_UNCHANGED) for f in image_files}

    print '\n\n{:*^70}\n'.format('PNG')

    output_files = [
        os.path.join(tempfile.gettempdir(), os.path.basename(f))
        for f in image_files
    ]

    start_time = time.time()

    write_images_to_files(images.values(), output_files)

    png_write_time = time.time() - start_time

    print 'Write images to PNG files:            {0:.2}        seconds'.format(
            png_write_time)

    png_size = 0
    for f in output_files:
        png_size += os.stat(f).st_size
    print 'Size of the resulting PNG files:      {0}        megabytes'.format(
            png_size / 10**6)

    start_time = time.time()

    read_images_from_files(image_files)

    png_read_time = time.time() - start_time

    print 'Read images from PNG files:           {0:.2}        seconds'.format(
            png_read_time)


    print '\n\n{:*^70}\n'.format('TIFF')

    output_files = [
        os.path.join(tempfile.gettempdir(),
                     re.sub(r'png', 'tiff', os.path.basename(f)))
        for f in image_files
    ]

    start_time = time.time()

    write_images_to_files(images.values(), output_files)

    passed_time = time.time() - start_time

    print 'Write images to TIFF files:           {0:.2}        seconds ({1}%)'.format(
            passed_time, int(np.float(passed_time) / np.float(png_write_time) * 100))

    size = 0
    for f in output_files:
        size += os.stat(f).st_size
    print 'Size of the resulting TIFF files:     {0}        megabytes ({1}%)'.format(
            size / 10**6, int(np.float(size) / np.float(png_size) * 100))

    start_time = time.time()

    read_images_from_files(image_files)

    passed_time = time.time() - start_time

    print 'Read images from TIFF files:          {0:.2}        seconds ({1}%)'.format(
            passed_time, int(np.float(passed_time) / np.float(png_read_time) * 100))

    print '\n\n{0:*^70}\n'.format('HDF5')

    print '\n{0:-^70}\n'.format('Without compression')

    start_time = time.time()

    write_images_to_hdf5_file(data_file, images)

    passed_time = time.time() - start_time

    print 'Write images to HDF5 file:            {0:.2}        seconds ({1}%)'.format(
            passed_time, int(np.float(passed_time) / np.float(png_write_time) * 100))

    size = os.stat(data_file).st_size
    print 'Size of the resulting HDF5 file:      {0}        megabytes ({1}%)'.format(
            size / 10**6, int(np.float(size) / np.float(png_size) * 100))

    start_time = time.time()

    read_images_from_hdf5_file(data_file, image_files)

    passed_time = time.time() - start_time

    print 'Read images from HDF5 file:           {0:.2}        seconds ({1}%)'.format(
            passed_time, int(np.float(passed_time) / np.float(png_read_time) * 100))

    compression_filters = {'gzip', 'lzf'}

    print '\n{0:-^70}\n'.format('With compression')

    for filt in compression_filters:

        print '"{0}"" compression filter'.format(filt)

        start_time = time.time()

        write_images_to_hdf5_file(data_file, images,
                                  compression_filter=filt)

        passed_time = time.time() - start_time

        print 'Write images to HDF5 file:            {0:.2}        seconds ({1}%)'.format(
            passed_time, int(np.float(passed_time) / np.float(png_write_time) * 100))

        size = os.stat(data_file).st_size
        print 'Size of the resulting HDF5 file:      {0}        megabytes ({1}%)'.format(
                size / 10**6, int(np.float(size) / np.float(png_size) * 100))

        start_time = time.time()

        read_images_from_hdf5_file(data_file, image_files)

        passed_time = time.time() - start_time

        print 'Read images from HDF5 file:           {0:.2}        seconds ({1}%)'.format(
                passed_time, int(np.float(passed_time) / np.float(png_read_time) * 100))

        print '\n'
