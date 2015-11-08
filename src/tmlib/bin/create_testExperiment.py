#! /usr/bin/env python
import os
import yaml
import numpy as np
import bioformats
import tempfile
import argparse
from tmlib.experiment import Experiment
from tmlib.writers import ImageWriter
from tmlib.writers import XmlWriter
from tmlib.cfg import IMAGE_NAME_FORMAT
from tmlib.metaconfig.ome_xml import XML_DECLARATION


def add_images_and_image_metadata(self, cycle):
    x_dim = 2
    y_dim = 2
    # Create images of one channel for one well
    name = '%s_%d' % (cycle.plate_name, cycle.index)
    metadata = bioformats.OMEXML(XML_DECLARATION)
    metadata.image_count = x_dim * y_dim
    plate = metadata.PlatesDucktype(metadata.root_node).newPlate(name=name)
    plate.RowNamingConvention = 'letter'
    plate.ColumnNamingConvention = 'number'
    plate.Rows = 1
    plate.Columns = 1
    well = metadata.WellsDucktype(plate).new(row=0, column=0)
    well_samples = metadata.WellSampleDucktype(well.node)
    with ImageWriter(cycle.image_dir) as writer:
        for y in xrange(y_dim):
            for x in xrange(x_dim):
                filename = IMAGE_NAME_FORMAT.format(
                                plate_name=name,
                                t=0, w='A01', y=y, x=x, c=0, z=0)
                img = np.random.random_integers(100, 140, (10, 10))
                writer.write(filename, img.astype(np.uint16))
                index = y*y_dim + x
                img_md = metadata.image(index)
                img_md.Name = filename
                img_md.ID = 'Image:%d' % index
                img_md.Pixels.plane_count = 1
                img_md.Pixels.Plane(0).TheT = 0
                img_md.Pixels.Plane(0).TheZ = 0
                img_md.Pixels.Plane(0).TheC = 0
                img_md.Pixels.SizeX = 100
                img_md.Pixels.SizeY = 100
                img_md.Pixels.Type = 'uint16'
                img_md.Pixels.Channel(0).ID = 'Channel:0'
                img_md.Pixels.Channel(0).Name = 'testChannel'
                well_samples.new(index=index)
                well_samples[index].ImageRef = img_md.ID
                well_samples[index].PositionX = x
                well_samples[index].PositionY = y

    with XmlWriter(cycle.dir) as writer:
        writer.write(cycle.image_metadata_file, metadata.to_xml())


if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.description = '''
        Create an experiment directory and populate it with mock data
        for integrated testing.
    '''

    parser.add_argument(
        '--dir', type=str, default=None,
        help='''
            root directory where the experiment should be created in
            (defaults to temporary directory)
        '''
    )
    parser.add_argument(
        '--name', type=str, default='testExperiment',
        help='''
            name that should be given to the experiment
            (default: "testExperiment")
        '''
    )
    parser.add_argument(
        '--image_conversion', action='store_true',
        help='''
            create the experiment in the state after
            the "image_conversion" tmaps workflow stage,
            i.e. populate the experiment with images and image metadata
        '''
    )
    parser.add_argument(
        '--image_preprocessing', action='store_true',
        help='''
            create the experiment in the state after
            the "image_conversion" tmaps workflow stage,
            i.e. populate the experiment with images, image metadata,
            illumination correction statistics and optionally alignment
            information
        '''
    )
    parser.add_argument(
        '-p', '--plates', type=int, default=2,
        help='''
            number of plates the experiment should have
        '''
    )
    parser.add_argument(
        '-c', '--cycles', type=int, default=2,
        help='''
            number of cycles each plate of the experiment should have
        '''
    )

    args = parser.parse_args()

    if args.dir:
        root_dir = args.dir
        if not os.path.exists(root_dir):
            raise OSError('Directory does not exist: %s' % root_dir)
    else:
        root_dir = tempfile.gettempdir()

    if args.image_conversion and args.image_preprocessing:
        raise ValueError('Only a single experiment state can be provided.')

    experiment_dir = os.path.join(root_dir, args.name)
    if not os.path.exists(experiment_dir):
        print 'create experiment: %s' % experiment_dir
        os.mkdir(experiment_dir)
    else:
        raise OSError('Experiment already exists: %s' % experiment_dir)
    # Add user configuration file
    user_cfg_file = os.path.join(experiment_dir, 'user.cfg.yml')
    user_cfg_settings = {
        'plates_dir': None,
        'sources_dir': None,
        'layers_dir': None,
        'plate_format': 384
    }
    with open(user_cfg_file, 'w') as f:
        f.write(yaml.dump(user_cfg_settings))
    experiment = Experiment(experiment_dir)

    if args.image_conversion or args.image_preprocessing:
        # Add two plates to the experiment, with two cycles each
        for p in range(args.plates):
            plate = experiment.add_plate('testPlate%d' % p)
            for c in range(args.cycles):
                cycle = plate.add_cycle()
                add_images_and_image_metadata(cycle)
