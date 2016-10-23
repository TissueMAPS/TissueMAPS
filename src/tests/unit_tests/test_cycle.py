import os
import numpy as np
import itertools
import bioformats
import fake_filesystem_unittest
from natsort import natsorted
from tmlib import cfg
from tmlib.cycle import Cycle


class TestCycle(fake_filesystem_unittest.TestCase):

    def setUp(self):
        self.setUpPyfakefs()
        self.data_location = '/testdir'
        os.mkdir(self.data_location)
        # Create an experiment on the fake file system
        self.experiment_name = 'testExperiment'
        self.experiment_dir = os.path.join(
                                self.data_location,
                                self.experiment_name)
        os.mkdir(self.experiment_dir)
        self.sources_dir = os.path.join(self.experiment_dir, 'sources')
        self.plates_dir = os.path.join(self.experiment_dir, 'plates')
        self.layers_dir = os.path.join(self.experiment_dir, 'layers')

        # Add a plate with one cycle to experiment
        os.mkdir(self.plates_dir)
        self.plate_name = 'testPlate'
        self.plate_dir = os.path.join(
                                self.plates_dir,
                                'plate_%s' % self.plate_name)
        os.mkdir(self.plate_dir)
        self.cycle_index = 0
        self.cycle_dir = os.path.join(
                                self.plate_dir,
                                'cycle_%.2d' % self.cycle_index)
        os.mkdir(self.cycle_dir)
        # Add image metadata file to cycle
        md = bioformats.OMEXML()
        # Add a plate element to metadata
        md.PlatesDucktype(md.root_node).newPlate(name='testPlate')
        plate = md.plates[0]
        plate.RowNamingConvention = 'letter'
        plate.ColumnNamingConvention = 'number'
        plate.Rows = 2
        plate.Columns = 3
        self.well_coordinates = list(itertools.product(
                        range(plate.Rows), range(plate.Columns)))
        self.n_wells = len(self.well_coordinates)
        n_well_samples = 4
        well_pos = [(0, 0), (0, 1), (1, 0), (1, 1)]
        # Add image elements to metadata
        md.image_count = self.n_wells * n_well_samples
        self.channel_name = 'testChannel'
        for i in xrange(md.image_count):
            image = md.image(i)
            image.ID = 'Image:%d' % i
            image.Pixels.plane_count = 1
            image.Pixels.SizeT = 1
            image.Pixels.SizeC = 1
            image.Pixels.SizeZ = 1
            image.Pixels.Plane(0).TheC = 0
            image.Pixels.Plane(0).TheT = 0
            image.Pixels.Plane(0).TheZ = 0
            image.Pixels.Channel(0).Name = self.channel_name
        # Add well elements to metadata
        for w, well_ix in enumerate(self.well_coordinates):
            well = md.WellsDucktype(plate).new(
                        row=well_ix[0],
                        column=well_ix[1])
            samples = md.WellSampleDucktype(well.node)
            for s in xrange(n_well_samples):
                samples.new(index=s)
                sample = samples[s]
                ix = w * n_well_samples + s
                image = md.image(ix)
                sample.ImageRef = image.ID
                sample.PositionY = well_pos[s][0]
                sample.PositionX = well_pos[s][1]
                image.Name = cfg.IMAGE_NAME_FORMAT.format(
                                plate_name=self.plate_name,
                                t=self.cycle_index,
                                w=w,
                                y=sample.PositionY,
                                x=sample.PositionX,
                                c=image.Pixels.Plane(0).TheC,
                                z=image.Pixels.Plane(0).TheZ)
        # Write metadata to file
        omexml = md.to_xml()
        self.metadata_file = os.path.join(
                                    self.cycle_dir,
                                    'image_metadata.ome.xml')
        with open(self.metadata_file, 'w') as f:
            f.write(omexml)

        # Add image files to cycle
        self.image_dir = os.path.join(self.cycle_dir, 'images')
        os.mkdir(self.image_dir)
        self.image_files = list()
        for i in xrange(md.image_count):
            filename = os.path.join(self.image_dir, md.image(i).Name)
            with open(filename, 'w') as f:
                f.write('')
            self.image_files.append(md.image(i).Name)

        self.cycle = Cycle(cycle_dir=self.cycle_dir)

        # Add illumination correction statistics file
        stats_dir = os.path.join(self.cycle_dir, 'stats')
        os.mkdir(stats_dir)
        self.stats_file = self.cycle.STATS_FILE_FORMAT.format(channel=0)
        filename = os.path.join(stats_dir, self.stats_file)
        with open(filename, 'w') as f:
            f.write('')

    def tearDown(self):
        self.tearDownPyfakefs()

    def test_initialize_cycle(self):
        self.assertEqual(self.cycle.dir, self.cycle_dir)
        self.assertEqual(self.cycle.index, self.cycle_index)

    def test_image_files(self):
        self.assertEqual(self.cycle.image_files, natsorted(self.image_files))

    def test_image_metadata(self):
        self.assertEqual(
            self.cycle.image_metadata['name'].tolist(),
            natsorted(self.image_files))
        self.assertEqual(
            self.cycle.image_metadata.loc[0, 'name'],
            self.image_files[0])
        self.assertEqual(
            len(np.unique(self.cycle.image_metadata['plate_name'])),
            1)
        self.assertEqual(
            self.cycle.image_metadata.loc[0, 'plate_name'],
            self.plate_name)
        self.assertEqual(
            len(np.unique(self.cycle.image_metadata['tpoint'])),
            1)
        self.assertEqual(
            self.cycle.image_metadata.loc[0, 'tpoint'],
            self.cycle_index)
        self.assertEqual(
            self.cycle.image_metadata.loc[0, 'channel'],
            0)
        self.assertEqual(
            self.cycle.image_metadata.loc[0, 'channel_name'],
            self.channel_name)
        self.assertEqual(
            self.cycle.image_metadata.loc[0, 'zplane'],
            0)

    def test_images(self):
        self.assertEqual(len(self.cycle.images), len(self.image_files))
        for i, f in enumerate(natsorted(self.image_files)):
            self.assertEqual(self.cycle.images[i].metadata.name, f)

    def test_illumstats_files(self):
        self.assertEqual(self.cycle.illumstats_files, [self.stats_file])

    def test_illumstats_metadata(self):
        self.assertEqual(self.cycle.illumstats_metadata[0].channel, 0)
        self.assertEqual(
            self.cycle.illumstats_metadata[0].filename,
            self.stats_file)
        self.assertEqual(
            self.cycle.illumstats_metadata[0].tpoint,
            self.cycle_index)
