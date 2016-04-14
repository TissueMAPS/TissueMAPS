import os
import logging
import numpy as np
import pandas as pd
import bioformats

import tmlib.models
from tmlib.workflow.metaconfig import metadata_handler_factory
from tmlib.workflow.metaconfig import metadata_reader_factory
from tmlib.workflow.api import ClusterRoutines
from tmlib.models.plate import determine_plate_dimensions
from tmlib.errors import MetadataError
from tmlib.workflow.registry import api

logger = logging.getLogger(__name__)


@api('metaconfig')
class MetadataConfigurator(ClusterRoutines):

    '''Class for configuration of microscope image metadata.

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

    def __init__(self, experiment_id, verbosity, **kwargs):
        '''
        Parameters
        ----------
        experiment_id: int
            ID of the processed experiment
        verbosity: int
            logging level
        **kwargs: dict
            ignored keyword arguments
        '''
        super(MetadataConfigurator, self).__init__(experiment_id, verbosity)

    def create_batches(self, args):
        '''Creates job descriptions for parallel computing.

        Parameters
        ----------
        args: tmlib.workflow.metaconfig.args.MetaconfigInitArgs
            step-specific arguments

        Returns
        -------
        Dict[str, List[dict] or dict]
            job descriptions
        '''
        job_descriptions = dict()
        job_descriptions['run'] = list()
        job_count = 0
        with tmlib.models.utils.Session() as session:
            acquisitions = session.query(tmlib.models.Acquisition).\
                join(tmlib.models.Plate).\
                join(tmlib.models.Experiment).\
                filter(tmlib.models.Experiment.id == self.experiment_id).\
                all()
            for acq in acquisitions:
                job_count += 1
                description = {
                    'id': job_count,
                    'inputs': {
                        'microscope_metadata_files': [
                            os.path.join(
                                acq.microscope_metadata_location, f.name
                            )
                            for f in acq.microscope_metadata_files
                        ]
                    },
                    'outputs': dict(),
                    'microscope_image_file_ids': [
                        f.id for f in acq.microscope_image_files
                    ],
                    'microscope_type': acq.plate.experiment.microscope_type,
                    'keep_zplanes': args.keep_zplanes,
                    'regex': args.regex,
                    'acquisition_id': acq.id,
                    'stitch_major_axis': args.stitch_major_axis,
                    'n_vertical': args.n_vertical,
                    'n_horizontal': args.n_horizontal,
                    'stitch_layout': args.stitch_layout
                }
                job_descriptions['run'].append(description)

            job_descriptions['collect'] = {
                'inputs': dict(),
                'outputs': dict()
            }

        return job_descriptions

    def delete_previous_job_output(self):
        '''Deletes all instances of class :py:class:`tmlib.models.Cycle`,
        :py:class:`tmlib.models.Well`, and :py:class:`tmlib.models.Channel` as
        well as all children for the processed experiment.
        '''
        with tmlib.models.utils.Session() as session:

            plate_ids = session.query(tmlib.models.Plate.id).\
                filter_by(experiment_id=self.experiment_id).\
                all()
            plate_ids = [p[0] for p in plate_ids]

        with tmlib.models.utils.Session() as session:

            logger.info('delete existing cycles')
            session.query(tmlib.models.Cycle).\
                filter(tmlib.models.Cycle.plate_id.in_(plate_ids)).\
                delete()

        with tmlib.models.utils.Session() as session:

            logger.info('delete existing wells')
            session.query(tmlib.models.Well).\
                filter(tmlib.models.Well.plate_id.in_(plate_ids)).\
                delete()

        with tmlib.models.utils.Session() as session:

            logger.info('delete existing channels')
            session.query(tmlib.models.Channel).\
                filter(tmlib.models.Channel.experiment_id == self.experiment_id).\
                delete()

    def run_job(self, batch):
        '''Formats OMEXML metadata extracted from microscope image files and
        complement it with metadata retrieved from additional microscope
        metadata files and/or user input.

        The actual processing is done by an implementation of the
        :py:class:`tmlib.workflow.metaconfig.default.MetadataHandler` abstract
        base class. Some file formats require additional customization,
        either because the `Bio-Formats` library does not fully support them or
        because the microscopes provides insufficient information in the files.
        To overcome these limitations, one can create a custom subclass
        of the `MetaHandler` abstract base class and overwrite its
        *ome_additional_metadata* property. Custom handlers already exists for
        the Yokogawa CellVoyager 7000 microscope ("cellvoyager")
        and Visitron microscopes ("visiview"). The list of custom
        handlers can be further extended by creating a new module in the
        `metaconfig` package with the same name as the corresponding file
        format. The module must contain a custom implementation of
        :py:class:`tmlib.workflow.metaconfig.default.MetadataHandler`,
        whose name has to be pretended with the capitalized name of the file
        format.

        See also
        --------
        :py:mod:`tmlib.workflow.metaconfig.default`
        :py:mod:`tmlib.workflow.metaconfig.cellvoyager`
        :py:mod:`tmlib.workflow.metaconfig.visiview`
        '''
        reader_class = metadata_reader_factory(
            batch['microscope_type']
        )

        with tmlib.models.utils.Session() as session:
            acquisition = session.query(tmlib.models.Acquisition).\
                get(batch['acquisition_id'])
            metadata_filenames = [
                f.location for f in acquisition.microscope_metadata_files
            ]
            omexml_images = {
                f.name: bioformats.OMEXML(f.omexml)
                for f in acquisition.microscope_image_files
            }

        with reader_class() as reader:
            omexml_metadata = reader.read(
                metadata_filenames, omexml_images.keys()
            )

        handler_class = metadata_handler_factory(
            batch['microscope_type']
        )

        mdhandler = handler_class(omexml_images, omexml_metadata)
        mdhandler.configure_omexml_from_image_files()
        mdhandler.configure_omexml_from_metadata_files(batch['regex'])
        missing = mdhandler.determine_missing_metadata()
        if missing:
            if batch['regex']:
                logger.warning('required metadata information is missing')
                logger.info(
                    'try to retrieve missing metadata from filenames '
                    'using regular expression'
                )
                n_wells = self.experiment.plate_format
                plate_dimensions = determine_plate_dimensions(n_wells)
                mdhandler.configure_metadata_from_filenames(
                    plate_dimensions=plate_dimensions,
                    regex=batch['regex']
                )
            else:
                raise MetadataError(
                    'The following metadata information is missing:\n"%s"\n'
                    'You can provide a regular expression in order to '
                    'retrieve the missing information from filenames '
                    % '", "'.join(missing)
                )
        missing = mdhandler.determine_missing_metadata()
        if missing:
            raise MetadataError(
                'The following metadata information is missing:\n"%s"\n'
                % '", "'.join(missing)
            )
        # Once we have collected basic metadata such as information about
        # channels and focal planes, we try to determine the relative position
        # of images within the acquisition grid
        try:
            logger.info(
                'try to determine grid coordinates from microscope '
                'stage positions'
            )
            mdhandler.determine_grid_coordinates_from_stage_positions()
        except MetadataError as error:
            logger.warning(
                'microscope stage positions are not available: "%s"'
                % str(error)
            )
            logger.info(
                'try to determine grid coordinates from provided stitch layout'
            )
            mdhandler.determine_grid_coordinates_from_layout(
                stitch_layout=batch['stitch_layout'],
                stitch_major_axis=batch['stitch_major_axis'],
                stitch_dimensions=(batch['n_vertical'], batch['n_horizontal'])
            )

        if not batch['keep_zplanes']:
            logger.info('project focal planes to 2D')
            mdhandler.reconfigure_ome_metadata_for_projection()
        else:
            logger.info('keep individual focal planes')

        # Create consistent zero-based ids
        # (some microscopes use one-based indexing)
        mdhandler.update_channel()
        mdhandler.update_zplane()
        mdhandler.assign_acquisition_site_indices()
        md = mdhandler.remove_redundant_columns()
        fmap = mdhandler.create_image_file_mapping()
        with tmlib.models.utils.Session() as session:
            acquisition = session.query(tmlib.models.Acquisition).\
                get(batch['acquisition_id'])

            for w in np.unique(md.well_name):
                w_index = np.where(md.well_name == w)[0]
                well = session.get_or_create(
                    tmlib.models.Well,
                    plate_id=acquisition.plate.id, name=w
                )

                for s in np.unique(md.loc[w_index, 'site']):
                    s_index = np.where(md.site == s)[0]
                    y = md.loc[s_index, 'well_position_y'].values[0]
                    x = md.loc[s_index, 'well_position_x'].values[0]
                    height = md.loc[s_index, 'height'].values[0]
                    width = md.loc[s_index, 'width'].values[0]
                    site = session.get_or_create(
                        tmlib.models.Site,
                        y=y, x=x, height=height, width=width, well_id=well.id
                    )

                    for index, i in md.ix[s_index].iterrows():
                        session.get_or_create(
                            tmlib.models.ImageFileMapping,
                            tpoint=i.tpoint, zplane=i.zplane,
                            site_id=site.id, map=fmap[index],
                            wavelength=i.channel_name,
                            acquisition_id=acquisition.id
                        )

    def collect_job_output(self, batch):
        '''Assigns registered image files from different acquisitions to
        separate *cycles*. If an acquisition includes multiple time points,
        a separate *cycle* is created for each time point.
        The mapping from *acquisitions* to *cycles* is consequently
        1 -> n, where n is the number of time points per acquisition (n >= 1).

        Whether acquisition time points will be interpreted as actual
        time points in a time series depends on the value of
        :py:attribute:`tmlib.models.Experiment.plate_acquisition_mode`.

        Parameters
        ----------
        batch: dict
            description of the *collect* job
        '''
        t_index = 0
        w_index = 0
        c_index = 0
        with tmlib.models.utils.Session() as session:
            for acq in session.query(tmlib.models.Acquisition).\
                    join(tmlib.models.Plate).\
                    join(tmlib.models.Experiment).\
                    filter(tmlib.models.Experiment.id == self.experiment_id):
                is_time_series_experiment = \
                    acq.plate.experiment.plate_acquisition_mode == 'series'
                is_multiplexing_experiment = \
                    acq.plate.experiment.plate_acquisition_mode == 'multiplexing'
                df = pd.DataFrame(
                    session.query(
                        tmlib.models.ImageFileMapping.tpoint,
                        tmlib.models.ImageFileMapping.wavelength,
                        tmlib.models.ImageFileMapping.zplane
                    ).
                    filter(tmlib.models.ImageFileMapping.acquisition_id == acq.id).
                    all()
                )
                tpoints = np.unique(df.tpoint)
                wavelengths = np.unique(df.wavelength)
                zplanes = np.unique(df.zplane)
                for t in tpoints:
                    cycle = session.get_or_create(
                        tmlib.models.Cycle,
                        index=c_index, tpoint=t_index, plate_id=acq.plate.id
                    )

                    for w in wavelengths:
                        if is_multiplexing_experiment:
                            name = 'cycle-%d_wavelength-%s' % (c_index, w)
                        channel = session.get_or_create(
                            tmlib.models.Channel,
                            name=name, index=w_index, wavelength=w,
                            experiment_id=acq.plate.experiment.id
                        )

                        for z in zplanes:
                            file_query = session.query(
                                tmlib.models.ImageFileMapping
                                ).\
                                filter_by(
                                    tpoint=t, zplane=z, wavelength=w,
                                    acquisition_id=acq.id
                                )
                            for im_file_mapping in file_query:
                                im_file_mapping.tpoint = t_index
                                im_file_mapping.cycle_id = cycle.id
                                im_file_mapping.channel_id = channel.id

                        if is_multiplexing_experiment:
                            w_index += 1

                    if is_time_series_experiment:
                        t_index += 1

                    c_index += 1


def factory(experiment_id, verbosity, **kwargs):
    '''Factory function for the instantiation of a `metaconfig`-specific
    implementation of the :py:class:`tmlib.workflow.api.ClusterRoutines`
    abstract base class.

    Parameters
    ----------
    experiment_id: int
        ID of the processed experiment
    verbosity: int
        logging level
    **kwargs: dict
        ignored keyword arguments

    Returns
    -------
    tmlib.workflow.metaextract.api.MetadataConfigurator
        API instance
    '''
    return MetadataConfigurator(experiment_id, verbosity, **kwargs)
