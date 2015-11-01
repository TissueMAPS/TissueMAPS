import os
import itertools
import bioformats
import fake_filesystem_unittest
from tmlib import cfg
from tmlib.plate import Plate


class TestPlate(fake_filesystem_unittest.TestCase):

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
        # Add a plate with one cycle
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
        # Add user configuration settings file
        self.user_cfg_settings = {
            'sources_dir': self.sources_dir,
            'plates_dir': self.plates_dir,
            'layers_dir': self.layers_dir,
            'plate_format': 384,
            'workflow': {
                'stages': [
                    {
                        'name': 'image_conversion',
                        'steps': [
                            {
                                'name': 'metaextract',
                                'args': dict()
                            }
                        ]
                    }
                ]
            }
        }
        self.user_cfg = cfg.UserConfiguration(
                        experiment_dir=self.experiment_dir,
                        cfg_settings=self.user_cfg_settings)
        # Add image metadata
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
        for i in xrange(md.image_count):
            image = md.image(i)
            image.Name = 'testImage%s' % i
            image.ID = 'Image:%d' % i
            image.Pixels.plane_count = 1
            image.Pixels.SizeT = 1
            image.Pixels.SizeC = 1
            image.Pixels.SizeZ = 1
            image.Pixels.Plane(0).TheC = 0
            image.Pixels.Plane(0).TheT = 0
            image.Pixels.Plane(0).TheZ = 0
            image.Pixels.Channel(0).Name = 'testChannel'
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
                sample.ImageRef = md.image(ix).ID
                sample.PositionY = well_pos[s][0]
                sample.PositionX = well_pos[s][1]
        # Write metadata to file
        omexml = md.to_xml()
        self.image_metadata_file = os.path.join(
                                    self.cycle_dir,
                                    'image_metadata.ome.xml')
        with open(self.image_metadata_file, 'w') as f:
            f.write(omexml)

    def tearDown(self):
        self.tearDownPyfakefs()

    def test_initialize_plate(self):
        plate = Plate(self.plate_dir, user_cfg=self.user_cfg, library='vips')
        self.assertEqual(plate.dir, self.plate_dir)
        self.assertEqual(plate.name, self.plate_name)
        self.assertEqual(plate.n_wells, self.user_cfg_settings['plate_format'])

    def test_cycles_attribute(self):
        plate = Plate(self.plate_dir, user_cfg=self.user_cfg, library='vips')
        self.assertEqual(len(plate.cycles), 1)
        self.assertEqual(plate.cycles[0].dir, self.cycle_dir)
        self.assertEqual(plate.cycles[0].index, self.cycle_index)
        self.assertEqual(plate.cycles[0].plate_name, self.plate_name)
        plate.add_cycle()
        self.assertEqual(len(plate.cycles), 2)
        self.assertEqual(plate.cycles[1].index, 1)

    def test_well_related_attributes(self):
        plate = Plate(self.plate_dir, user_cfg=self.user_cfg, library='vips')
        self.assertEqual(plate.n_acquired_wells, self.n_wells)
        self.assertEqual(plate.dimensions, (16, 24))
        self.assertEqual(plate.well_coordinates, self.well_coordinates)

    def test_well_related_methods(self):
        well_coordinate = Plate.map_well_id_to_coordinate('A02')
        self.assertEqual(well_coordinate, (1, 2))
        well_id = Plate.map_well_coordinate_to_id((1, 2))
        self.assertEqual(well_id, 'A02')
