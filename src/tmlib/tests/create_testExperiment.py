#! /usr/bin/env python
import os
import yaml
import numpy as np
import bioformats
from tmlib.experiment import Experiment
from tmlib.writers import ImageWriter
from tmlib.writers import XmlWriter
from tmlib.cfg import IMAGE_NAME_FORMAT
from tmlib.metaconfig.ome_xml import XML_DECLARATION


def add_images(self, cycle):
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

    data_location = os.path.join(os.path.dirname(__file__), 'testdata')
    # Create an experiment on the fake file system
    experiment_name = 'testExperiment'
    experiment_dir = os.path.join(data_location, experiment_name)
    os.mkdir(experiment_dir)
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
    # Add two plates to the experiment, with two cycles each
    plate_1 = self.experiment.add_plate('testPlate1')
    plate_1_cycle_1 = plate_1.add_cycle()
    add_images(plate_1_cycle_1)
    plate_1_cycle_2 = plate_1.add_cycle()
    add_images(plate_1_cycle_2)
    plate_2 = self.experiment.add_plate('testPlate2')
    plate_2_cycle_1 = plate_2.add_cycle()
    add_images(plate_2_cycle_1)
    plate_2_cycle_2 = plate_2.add_cycle()
    add_images(plate_2_cycle_2)
