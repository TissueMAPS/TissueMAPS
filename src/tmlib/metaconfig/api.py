import os
import re
import logging
import importlib
import numpy as np
import pandas as pd
from .. import cfg
from ..plate import determine_plate_dimensions
from ..metadata import ImageFileMapping
from ..api import ClusterRoutines
from ..writers import JsonWriter
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

    def __init__(self, experiment, prog_name, verbosity, **kwargs):
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
        kwargs: dict
            mapping of additional key-value pairs that are ignored
        '''
        super(MetadataConfigurator, self).__init__(
                experiment, prog_name, verbosity)

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

    def create_job_descriptions(self, args):
        '''
        Create job descriptions for parallel computing.

        Parameters
        ----------
        args: tmlib.metaconfig.args.MetaconfigInitArgs
            step-specific arguments

        Returns
        -------
        Dict[str, List[dict] or dict]
            job descriptions
        '''
        if args.file_format != 'default':
            if args.file_format not in Formats.SUPPORT_FOR_ADDITIONAL_FILES:
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
                                         acquisition.image_mapping_file)
                        ]
                    },
                    'file_format': args.file_format,
                    'keep_z_stacks': args.keep_z_stacks,
                    'plate': source.index,
                    'regex': args.regex,
                    'stitch_major_axis': args.stitch_major_axis,
                    'n_vertical': args.n_vertical,
                    'n_horizontal': args.n_horizontal,
                    'stitch_layout': args.stitch_layout
                }
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
                                 acquisition.image_mapping_file)
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
                                 source.image_mapping_file)
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
        :py:mod:`tmlib.metaconfig.default`
        :py:mod:`tmlib.metaconfig.cellvoyager`
        :py:mod:`tmlib.metaconfig.visiview`
        '''
        handler_class = self._handler_factory(batch['file_format'])
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
                    stitch_dimensions=(batch['n_vertical'],
                                       batch['n_horizontal']))

        if not batch['keep_z_stacks']:
            logger.info('project focal planes to 2D')
            handler.reconfigure_ome_metadata_for_projection()
        else:
            logger.info('keep individual focal planes')

        # Create consistent zero-based ids
        # (some microscopes use one-based indexing)
        handler.update_channel_index()
        handler.update_zplane_index()
        handler.build_image_filenames(self.image_file_format_string)
        handler.assign_acquisition_site_indices()
        md = handler.remove_redundant_columns()
        fmap = handler.create_image_file_mapper()
        self._write_metadata_to_file(batch['outputs']['metadata_files'][0], md)
        self._write_mapper_to_file(batch['outputs']['mapper_files'][0], fmap)

    @staticmethod
    def _write_metadata_to_file(filename, metadata):
        store = pd.HDFStore(filename, 'w')  # truncate file!
        store.put('metadata', metadata, format='table', data_columns=True)
        store.close()

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
        file_mapper = list()
        for i, source in enumerate(self.experiment.sources):
            # Create new plate
            self.experiment.add_plate()
            cycle_count = 0
            for acquisition in source.acquisitions:

                metadata = acquisition.image_metadata

                tpoints = np.unique(metadata.tpoint_ix)
                logger.info('%d time points found in source directory "%s"',
                            len(tpoints), os.path.basename(acquisition.dir))

                # Create a cycle for each acquired time point
                for t in tpoints:

                    logger.info('update metadata information for cycle #%d',
                                cycle_count)
                    try:
                        cycle = self.experiment.plates[i].cycles[cycle_count]
                    except IndexError:
                        # Create cycle if it doesn't exist
                        cycle = self.experiment.plates[i].add_cycle()

                    # Create a metadata subset that only contains information
                    # about image elements belonging to the currently processed
                    # cycle (time point)
                    md = metadata[metadata.tpoint_ix == t]
                    for ix in md.index:
                        # Update name according to new time point index
                        # TODO: In case of a acquistion_mode "series" increment
                        # time and "multiplexing" increment channel index.
                        # Time point and cycle index may then no longer be
                        # identical!!!
                        md.at[ix, 'tpoint_ix'] = cycle_count
                        fieldnames = {
                            'p': md.at[ix, 'plate_ix'],
                            'w': md.at[ix, 'well_name'],
                            'y': md.at[ix, 'well_position_y'],
                            'x': md.at[ix, 'well_position_x'],
                            'c': md.at[ix, 'channel_ix'],
                            'z': md.at[ix, 'zplane_ix'],
                            't': md.at[ix, 'tpoint_ix'],
                        }
                        md.at[ix, 'name'] = cfg.IMAGE_NAME_FORMAT.format(
                                                        **fieldnames)

                    # Add the corresponding plate name
                    md.plate_ix = pd.Series(
                        np.repeat(source.index, md.shape[0])
                    )

                    # Update "ref_index" and "name" in the file mapper with the
                    # path to the final image file relative to the experiment
                    # root directory
                    for element in acquisition.image_mapping:
                        new_element = ImageFileMapping
                    ()
                        new_element.series = element.series
                        new_element.planes = element.planes
                        # Since we assigned new indices, we have to map the
                        # the reference back
                        ref_md = metadata.iloc[element.ref_index]
                        ix = np.where(
                            (md.well_name == ref_md.well_name) &
                            (md.well_position_y == ref_md.well_position_y) &
                            (md.well_position_x == ref_md.well_position_x) &
                            (md.channel_ix == ref_md.channel_ix) &
                            (md.zplane_ix == ref_md.zplane_ix)
                        )[0]
                        if len(ix) > 1:
                            raise ValueError('One than one reference found.')
                        new_element.ref_index = ix[0]
                        # Update name in the file mapper and make path relative
                        new_element.ref_file = os.path.relpath(os.path.join(
                                cycle.image_dir,
                                md.at[new_element.ref_index, 'name']
                            ),
                            self.experiment.plates_dir
                        )
                        # Make path to source files relative
                        new_element.files = [
                            os.path.relpath(
                                os.path.join(acquisition.image_dir, f),
                                self.experiment.sources_dir)
                            for f in element.files
                        ]
                        file_mapper.append(dict(new_element))

                    # Sort metadata according to name and reset indices
                    md = md.sort_values('name')
                    md.index = range(md.shape[0])

                    # Store the updated metadata in an HDF5 file
                    filename = os.path.join(cycle.dir,
                                            cycle.image_metadata_file)
                    store = pd.HDFStore(filename, 'w')
                    store.append('metadata', md,
                                 format='table', data_columns=True)
                    store.close()

                    # Remove the intermediate cycle-specific mapper file
                    os.remove(os.path.join(acquisition.dir,
                              acquisition.image_mapping_file))

                    cycle_count += 1

                with JsonWriter() as writer:
                    filename = batch['outputs']['mapper_files'][i]
                    writer.write(filename, file_mapper)

    def apply_statistics(self, output_dir, plates, wells, sites, channels,
                         tpoints, zplanes, **kwargs):
        '''
        Not implemented.
        '''
        raise AttributeError('"%s" object doesn\'t have a "apply_statistics"'
                             ' method' % self.__class__.__name__)
