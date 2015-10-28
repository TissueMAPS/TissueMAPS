import os
import re
import logging
import importlib
import pandas as pd
import bioformats
from collections import defaultdict
from .ome_xml import XML_DECLARATION
from .. import utils
from .. import cfg
from ..plate import determine_plate_dimensions
from ..metadata import ImageFileMapper
from ..cluster import ClusterRoutines
from ..writers import JsonWriter
from ..writers import XmlWriter
from ..errors import NotSupportedError
from ..errors import MetadataError
from ..formats import Formats

logger = logging.getLogger(__name__)


class MetadataConfigurator(ClusterRoutines):

    '''
    Abstract base class for the handling of image metadata.

    It provides methods for conversion of metadata extracted from heterogeneous
    microscope file formats using the
    `Bio-Formats <http://www.openmicroscopy.org/site/products/bio-formats>`_
    library into a custom format. The original metadata has to be available
    in OMEXML format according to the
    `OME schema <http://www.openmicroscopy.org/Schemas/Documentation/Generated/OME-2015-01/ome.html>`_.

    The class further provides methods to complement the automatically
    retrieved metadata by making use of additional microscope-specific metadata
    files and/or user input.

    The metadata corresponding to the final PNG images are stored in a
    separate JSON file.
    '''

    def __init__(self, experiment, prog_name, verbosity):
        '''
        Initialize an instance of class MetadataConfigurator.

        Parameters
        ----------
        experiment: tmlib.experiment.Experiment
            configured experiment object
        prog_name: str
            name of the corresponding program (command line interface)
        verbosity: int
            logging level

        Returns
        -------
        tmlib.metaconfig.api.MetadataConfigurator

        Raises
        ------
        NotSupportedError
            when `file_format` is not supported
        '''
        super(MetadataConfigurator, self).__init__(
                experiment, prog_name, verbosity)
        self.experiment = experiment
        self.prog_name = prog_name
        self.verbosity = verbosity

    @property
    def image_file_format_string(self):
        '''
        Returns
        -------
        image_file_format_string: str
            format string that specifies how the names of the final image
            files should be formatted
        '''
        return cfg.IMAGE_NAME_FORMAT

    def create_job_descriptions(self, **kwargs):
        '''
        Create job descriptions for parallel computing.

        Parameters
        ----------
        **kwargs: dict
            no additional arguments used

        Returns
        -------
        Dict[str, List[dict] or dict]
            job descriptions
        '''
        if kwargs['format'] != 'default':
            if kwargs['format'] not in Formats.SUPPORT_FOR_ADDITIONAL_FILES:
                raise NotSupportedError(
                        'The specified format is not supported.\n'
                        'Possible options are: "%s"'.format(
                            '", "'.join(Formats.SUPPORT_FOR_ADDITIONAL_FILES)))
        job_descriptions = dict()
        job_descriptions['run'] = list()
        job_count = 0
        for source in self.experiment.sources:
            for acquisition in source.acquisitions:
                job_count += 1
                description = {
                    'id': job_count,
                    'inputs': {
                        'uploaded_image_files': [
                            os.path.join(acquisition.image_dir, f)
                            for f in acquisition.image_files
                        ],
                        'uploaded_additional_files': [
                            os.path.join(acquisition.metadata_dir, f)
                            for f in acquisition.additional_files
                        ],
                        'omexml_files': [
                            os.path.join(acquisition.omexml_dir, f)
                            for f in acquisition.omexml_files
                        ]
                    },
                    'outputs': {
                        'metadata_files': [
                            os.path.join(acquisition.dir,
                                         acquisition.image_metadata_file)
                        ],
                        'mapper_files': [
                            os.path.join(acquisition.dir,
                                         acquisition.image_mapper_file)
                        ]
                    },
                    'z_stacks': kwargs['z_stacks'],
                    'plate': source.name
                }
                description.update(kwargs)
                job_descriptions['run'].append(description)

        job_descriptions['collect'] = {
            'inputs': {
                'metadata_files': [
                    os.path.join(acquisition.dir,
                                 acquisition.image_metadata_file)
                    for source in self.experiment.sources
                    for acquisition in source.acquisitions
                ],
                'mapper_files': [
                    os.path.join(acquisition.dir,
                                 acquisition.image_mapper_file)
                    for source in self.experiment.sources
                    for acquisition in source.acquisitions
                ]
            },
            'outputs': {
                'plates_dir': [
                    self.experiment.plates_dir
                ],
                'mapper_files': [
                    os.path.join(source.dir,
                                 source.image_mapper_file)
                    for source in self.experiment.sources
                ]
            },
            'removals': ['mapper_files']
        }

        return job_descriptions

    def _handler_factory(self, file_format):
        module_name = re.sub(r'([^.]\w+)$', file_format, __name__)
        logger.debug('import module for specified format "%s"' % module_name)
        module_inst = importlib.import_module(module_name)
        class_name = '%sMetadataHandler' % file_format.capitalize()
        logger.debug('instantiate metadata handler class "%s"' % class_name)
        class_inst = getattr(module_inst, class_name)
        return class_inst

    def run_job(self, batch):
        '''
        Format the OMEXML metadata extracted from image files, complement it
        with metadata retrieved from additional files and/or user input
        and write the formatted metadata to a JSON file.

        The actual processing is done by `MetadataHandler` classes. Some file
        formats require additional customization, either because Bio-Formats
        does not fully support them or because the microscopes provides
        insufficient information in the image files.
        To overcome these limitations, one can create a custom subclass
        of the `MetaHandler` abstract base class and overwrite its
        *ome_additional_metadata* property. Custom handlers already exists for
        the Yokogawa CellVoyager 7000 microscope ("cellvoyager")
        and Visitron microscopes ("visiview"). The list of custom
        handlers can be further extended by creating a new module in the
        `metaconfig` package with the same name as the corresponding file
        format. The module must contain the custom `MetaHandler` subclass,
        whose name has to be pretended with the capitalized name of the file
        format. For example, given a file format called "NewMicroscope" one
        would need to create the module "tmlib.metaconfig.newmicroscope", which
        would contain a class named "NewmicroscopeMetadataHandler"
        that inherits from `MetadataHandler` and overwrites the abstract
        methods. The new handler class would then be automatically picked up
        and used when the value of the "format" argument is "newmicroscope".

        See also
        --------
        :mod:`tmlib.metaconfig.default`
        :mod:`tmlib.metaconfig.cellvoyager`
        :mod:`tmlib.metaconfig.visiview`
        '''
        handler_class = self._handler_factory(batch['format'])
        handler = handler_class(
                            batch['inputs']['uploaded_image_files'],
                            batch['inputs']['uploaded_additional_files'],
                            batch['inputs']['omexml_files'],
                            batch['plate'])

        handler.configure_ome_metadata_from_image_files()
        handler.configure_ome_metadata_from_additional_files()
        missing_md = handler.determine_missing_metadata()
        if missing_md:
            if batch['regex'] or handler.REGEX:
                logger.warning('required metadata information is missing')
                logger.info('try to retrieve missing metadata from filenames '
                            'using regular expression')
                n_wells = self.experiment.user_cfg.plate_format
                plate_dimensions = determine_plate_dimensions(n_wells)
                handler.configure_metadata_from_filenames(
                    plate_dimensions=plate_dimensions, regex=batch['regex'])
            else:
                raise MetadataError(
                    'The following metadata information is missing:\n"%s"\n'
                    'You can provide a regular expression in order to '
                    'retrieve the missing information from filenames '
                    % '", "'.join(missing_md))
        missing_md = handler.determine_missing_metadata()
        if missing_md:
            raise MetadataError(
                    'The following metadata information is missing:\n"%s"\n'
                    % '", "'.join(missing_md))
        # Once we have collected basic metadata such as information about
        # channels and focal planes, we try to determine the relative position
        # of images within the acquisition grid
        try:
            logger.info('try to determine grid coordinates from microscope '
                        'stage positions')
            handler.determine_grid_coordinates_from_stage_positions()
        except MetadataError as error:
            logger.warning('microscope stage positions are not available: "%s"'
                           % str(error))
            logger.info('try to determine grid coordinates from provided '
                        'stitch layout')
            handler.determine_grid_coordinates_from_layout(
                    stitch_layout=batch['stitch_layout'],
                    stitch_major_axis=batch['stitch_major_axis'],
                    stitch_dimensions=(batch['stitch_vertical'],
                                       batch['stitch_horizontal']))

        if batch['z_stacks']:
            logger.info('project focal planes to 2D')
            handler.reconfigure_ome_metadata_for_projection()
        else:
            logger.info('keep individual focal planes')
        # Create consistent zero-based ids
        # (some microscopes use one-based indexing)
        handler.update_channel_ixs()
        handler.update_zplane_ixs()
        md = handler.build_image_filenames(self.image_file_format_string)
        fmap = handler.create_image_file_mapper()
        self._write_metadata_to_file(batch['outputs']['metadata_files'][0], md)
        self._write_mapper_to_file(batch['outputs']['mapper_files'][0], fmap)

    @staticmethod
    def _write_metadata_to_file(filename, metadata):
        with XmlWriter() as writer:
            data = metadata.to_xml()
            logger.info('write configured metadata to file')
            writer.write(filename, data)

    @staticmethod
    def _write_mapper_to_file(filename, hashmap):
        with JsonWriter() as writer:
            logger.info('write file mapper to file')
            writer.write(filename, hashmap)

    def collect_job_output(self, batch):
        '''
        Collect the configured image metadata from different sources and
        assign them to separate *cycles*. If a source contains images from
        more than one time points, a separate *cycle* is created for each time
        point. The mapping from *acquisitions* to *cycles* is consequently
        1 -> n, where n is the number of time points per acquisition (n >= 1).

        The file mappings created for each source are also collected and fused.
        They final mapping contains all the information required for the
        extraction of images from the original source image files in the
        `imextract` step.

        Parameters
        ----------
        batch: dict
            description of the *collect* job
        '''
        plate_file_mapper = list()
        for i, source in enumerate(self.experiment.sources):
            # Create new plate
            self.experiment.add_plate(source.name)
            cycle_count = 0
            for acquisition in source.acquisitions:

                metadata = acquisition.image_metadata

                # Create a lookup tables for well information
                tpoint_samples = defaultdict(list)
                plate = metadata.plates[0]
                for w, well_id in enumerate(plate.Well):
                    for s in plate.Well[w].Sample:
                        ref_id = s.ImageRef
                        ref_ix = int(re.search(
                                     r'Image:(\d+)$', ref_id).group(1))
                        ref_im = metadata.image(ref_ix)
                        c = ref_im.Pixels.Channel(0).Name
                        t = ref_im.Pixels.Plane(0).TheT
                        k = (w, s.PositionY, s.PositionX, c, t)
                        tpoint_samples[k].append(ref_id)

                ids = utils.flatten(tpoint_samples.values())
                # NOTE: There should be only one value per key
                lut = pd.DataFrame(tpoint_samples.keys())
                lut.columns = ['w', 'y', 'x', 'c', 't']

                tpoints = lut['t'].tolist()
                unique_tpoints = set(tpoints)
                logger.info('%d time points found in source directory "%s"',
                            len(unique_tpoints),
                            os.path.basename(acquisition.dir))

                # Create a cycle for each acquired time point
                for t in unique_tpoints:

                    logger.info('update metadata information for cycle #%d',
                                cycle_count)
                    try:
                        cycle = self.experiment.plates[i].cycles[cycle_count]
                    except IndexError:
                        # Create cycle if it doesn't exist
                        cycle = self.experiment.plates[i].add_cycle()

                    cycle_indices = lut[lut['t'] == t].index.tolist()

                    # Create a new metadata object that only contains *Image*
                    # elements belonging to the currently processed cycle
                    # (time point)
                    cycle_metadata = bioformats.OMEXML(XML_DECLARATION)
                    cycle_metadata.image_count = len(cycle_indices)

                    # Create a plate element, where wells only contain the samples
                    # that belong to the currently processed cycle (time point)
                    cpla = cycle_metadata.PlatesDucktype(
                                    cycle_metadata.root_node).newPlate(
                                        name=cycle.name)
                    upla = metadata.plates[0]
                    cpla.RowNamingConvention = upla.RowNamingConvention
                    cpla.ColumnNamingConvention = upla.ColumnNamingConvention
                    cpla.Rows = upla.Rows
                    cpla.Columns = upla.Columns
                    im_count = 0
                    fm_lut = dict()
                    for w, well_id in enumerate(plate.Well):
                        well = cycle_metadata.WellsDucktype(cpla).new(
                            row=upla.Well[w].Row, column=upla.Well[w].Column)
                        samples = cycle_metadata.WellSampleDucktype(well.node)
                        well_ix = lut[
                            (lut['w'] == w) & (lut['t'] == t)
                        ].index.tolist()
                        for s, ix in enumerate(well_ix):
                            samples.new(index=s)
                            samples[s].PositionX = lut.iloc[ix]['x']
                            samples[s].PositionY = lut.iloc[ix]['y']
                            ref_id = ids[ix]
                            ref_ix = int(re.search(
                                         r'Image:(\d+)$', ref_id).group(1))
                            ref_im = metadata.image(ref_ix)
                            # Create a new *Image* element
                            im = cycle_metadata.image(im_count)
                            # Copy the contents of the reference
                            im.AcquisitionDate = ref_im.AcquisitionDate
                            pxl = im.Pixels
                            pxl.plane_count = 1
                            pxl.Channel(0).Name = ref_im.Pixels.Channel(0).Name
                            pxl.PixelType = ref_im.Pixels.PixelType
                            pxl.SizeX = ref_im.Pixels.SizeX
                            pxl.SizeY = ref_im.Pixels.SizeY
                            pxl.SizeT = 1
                            pxl.SizeC = 1
                            pxl.SizeZ = 1
                            pln = pxl.Plane(0)
                            pln.TheT = ref_im.Pixels.Plane(0).TheT
                            pln.TheZ = ref_im.Pixels.Plane(0).TheZ
                            pln.TheC = ref_im.Pixels.Plane(0).TheC
                            pln.PositionY = ref_im.Pixels.Plane(0).PositionY
                            pln.PositionX = ref_im.Pixels.Plane(0).PositionX
                             # Assign a new ID
                            im.ID = 'Image:%d' % im_count
                            # Update the time point (cycle identifier)
                            im.Pixels.Plane(0).TheT = cycle_count
                            # Update the name
                            fn = {
                                'plate_name': source.name,
                                'w': well_id,
                                'y': int(samples[s].PositionY),
                                'x': int(samples[s].PositionX),
                                'c': im.Pixels.Plane(0).TheC,
                                'z': im.Pixels.Plane(0).TheZ,
                                't': im.Pixels.Plane(0).TheT
                            }
                            im.Name = self.image_file_format_string.format(**fn)
                            samples[s].ImageRef = im.ID
                            # Map original index to new cycle-specific index
                            fm_lut[ref_ix] = im_count
                            im_count += 1

                    # Store the updated metadata as XML in the cycle directory
                    with XmlWriter() as writer:
                        filename = os.path.join(cycle.dir,
                                                cycle.image_metadata_file)
                        data = cycle_metadata.to_xml()
                        writer.write(filename, data)

                    # Update "ref_index" and "name" in the filemapper with the
                    # full path to the final image file (in the respective cycle
                    # folder) and store it in the main upload directory
                    # TODO
                    file_mapper = acquisition.image_mapper
                    for element in file_mapper:
                        new_element = ImageFileMapper()
                        ix = fm_lut[element.ref_index]
                        new_element.series = element.series
                        new_element.planes = element.planes
                        new_element.files = [
                            os.path.join(acquisition.dir,
                                         acquisition.image_dir, f)
                            for f in element.files
                        ]
                        new_element.ref_index = ix
                        new_element.ref_id = cycle_metadata.image(ix).ID
                        new_element.ref_file = os.path.join(
                            cycle.image_dir,
                            cycle_metadata.image(ix).Name
                        )
                        plate_file_mapper.append(dict(new_element))

                    # Remove the intermediate cycle-specific mapper file
                    os.remove(os.path.join(acquisition.dir,
                              acquisition.image_mapper_file))

                    cycle_count += 1

                with JsonWriter() as writer:
                    filename = batch['outputs']['mapper_files'][i]
                    data = plate_file_mapper
                    writer.write(filename, data)

    def apply_statistics(self, output_dir, plates, wells, sites, channels,
                         tpoints, zplanes, **kwargs):
        '''
        Not implemented.
        '''
        raise AttributeError('"%s" object doesn\'t have a "apply_statistics"'
                             ' method' % self.__class__.__name__)
