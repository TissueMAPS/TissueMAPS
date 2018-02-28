# TmLibrary - TissueMAPS library for distibuted image analysis routines.
# Copyright (C) 2016  Markus D. Herrmann, University of Zurich and Robin Hafen
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
import os
import logging
import numpy as np
import pandas as pd
import bioformats

import tmlib.models as tm
from tmlib.workflow.metaconfig import metadata_handler_factory
from tmlib.workflow.metaconfig import metadata_reader_factory
from tmlib.workflow.metaconfig import get_microscope_type_regex
from tmlib.workflow.api import WorkflowStepAPI
from tmlib.errors import MetadataError
from tmlib.workflow import register_step_api

logger = logging.getLogger(__name__)


@register_step_api('metaconfig')
class MetadataConfigurator(WorkflowStepAPI):

    '''Class for configuration of microscope image metadata.

    It provides methods for conversion of metadata extracted from heterogeneous
    microscope file formats into a `TissueMAPS`-specific schema.
    The original metadata has to be available in OMEXML format according to the
    `OME schema <http://www.openmicroscopy.org/Schemas/Documentation/Generated/OME-2015-01/ome.html>`_.

    The class further provides methods to complement the metadata retrieved
    via `Bio-Formats <http://www.openmicroscopy.org/site/products/bio-formats>`_
    with information available from of additional microscope-specific metadata
    files and/or user input.

    '''

    def __init__(self, experiment_id):
        '''
        Parameters
        ----------
        experiment_id: int
            ID of the processed experiment
        '''
        super(MetadataConfigurator, self).__init__(experiment_id)

    def create_run_batches(self, args):
        '''Creates job descriptions for parallel processing.

        Parameters
        ----------
        args: tmlib.workflow.metaconfig.args.MetaconfigBatchArguments
            step-specific batch arguments

        Returns
        -------
        generator
            job descriptions
        '''
        job_count = 0

        with tm.utils.ExperimentSession(self.experiment_id) as session:
            experiment = session.query(tm.Experiment).one()
            for acq in session.query(tm.Acquisition):
                job_count += 1
                image_files = session.query(tm.MicroscopeImageFile.id).\
                    filter_by(acquisition_id=acq.id).\
                    all()
                yield {
                    'id': job_count,
                    'microscope_image_file_ids': [f.id for f in image_files],
                    'microscope_type': experiment.microscope_type,
                    'regex': args.regex,
                    'acquisition_id': acq.id,
                    'n_vertical': args.n_vertical,
                    'n_horizontal': args.n_horizontal,
                    'stitch_layout': args.stitch_layout,
                    'perform_mip': args.mip
                }

    def delete_previous_job_output(self):
        '''Deletes all instances of class :class:`tm.Cycle`,
        :class:`tm.Well`, and :class:`tm.Channel` as
        well as all children for the processed experiment.
        '''
        # Distributed tables cannot be dropped within a transaction
        with tm.utils.ExperimentSession(self.experiment_id, False) as session:
            logger.info('delete existing channel layers')
            session.query(tm.ChannelLayerTile).delete()
            session.query(tm.ChannelLayer).delete()
            logger.info('delete existing channels')
            session.query(tm.Channel).delete()
            logger.info('delete existing cycles')
            session.query(tm.Cycle).delete()
            logger.info('delete existing wells')
            session.query(tm.Well).delete()

    def run_job(self, batch, assume_clean_state=False):
        '''Configures OMEXML metadata extracted from microscope image files and
        complements it with metadata retrieved from additional microscope
        metadata files and/or user input.

        The actual processing is delegated to a format-specific implementation of
        :class:`MetadataHandler <tmlib.workflow.metaconfig.base.MetadataHandler>`.

        Parameters
        ----------
        batch: dict
            job description
        assume_clean_state: bool, optional
            assume that output of previous runs has already been cleaned up

        See also
        --------
        :mod:`tmlib.workflow.metaconfig.cellvoyager`
        '''
        regexp = batch.get('regex', '')
        if not regexp:
            regexp = get_microscope_type_regex(
                batch['microscope_type'], as_string=True
            )[0]
        with tm.utils.ExperimentSession(self.experiment_id) as session:
            experiment = session.query(tm.Experiment).one()
            plate_dimensions = experiment.plates[0].dimensions
            acquisition = session.query(tm.Acquisition).\
                get(batch['acquisition_id'])
            metadata_files = session.query(tm.MicroscopeMetadataFile.location).\
                filter_by(acquisition_id=batch['acquisition_id']).\
                all()
            metadata_filenames = [f.location for f in metadata_files]
            image_files = session.query(
                    tm.MicroscopeImageFile.name, tm.MicroscopeImageFile.omexml
                ).\
                filter_by(acquisition_id=batch['acquisition_id']).\
                all()
            omexml_images = {
                f.name: bioformats.OMEXML(f.omexml) for f in image_files
            }

        MetadataReader = metadata_reader_factory(batch['microscope_type'])
        if MetadataReader is not None:
            with MetadataReader() as mdreader:
                omexml_metadata = mdreader.read(
                    metadata_filenames, omexml_images.keys()
                )
        else:
            omexml_metadata = None

        MetadataHandler = metadata_handler_factory(batch['microscope_type'])
        mdhandler = MetadataHandler(omexml_images, omexml_metadata)
        mdhandler.configure_from_omexml()
        missing = mdhandler.determine_missing_metadata()
        if missing:
            logger.warning(
                'required metadata information is missing: "%s"',
                '", "'.join(missing)
            )
            logger.info(
                'try to retrieve missing metadata from filenames '
                'using regular expression'
            )
            if regexp is None:
                logger.warn('no regular expression provided')
            mdhandler.configure_from_filenames(
                plate_dimensions=plate_dimensions, regex=regexp
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
            # In general, the values of these arguments can be ``None``, because
            # they are not required and may not be used.
            # However, in case the grid coordinates should be determined based
            # on user interput, these arguments are required.
            if not isinstance(batch['n_vertical'], int):
                raise TypeError(
                    'Value of argument "n_vertical" must be an integer.'
                )
            if not isinstance(batch['n_horizontal'], int):
                raise TypeError(
                    'Value of argument "n_horizontal" must be an integer.'
                )
            mdhandler.determine_grid_coordinates_from_layout(
                stitch_layout=batch['stitch_layout'],
                stitch_dimensions=(batch['n_vertical'], batch['n_horizontal'])
            )

        if batch['perform_mip']:
            mdhandler.group_metadata_per_zstack()

        # Create consistent zero-based ids
        mdhandler.update_indices()
        mdhandler.assign_acquisition_site_indices()
        md = mdhandler.remove_redundant_columns()
        fmaps = mdhandler.create_image_file_mappings()

        logger.info('create database entries')

        with tm.utils.ExperimentSession(self.experiment_id) as session:
            channels = dict()
            bit_depth = md['bit_depth'][0]
            for ch_name in np.unique(md['channel_name']):
                logger.info('create channel "%s"', ch_name)
                ch = session.get_or_create(
                    tm.Channel, experiment_id=self.experiment_id,
                    name=ch_name, wavelength=ch_name, bit_depth=bit_depth,
                )
                channels[ch_name] = ch.id

        for w in np.unique(md.well_name):

            with tm.utils.ExperimentSession(self.experiment_id) as session:
                acquisition = session.query(tm.Acquisition).\
                    get(batch['acquisition_id'])

                logger.info('create well "%s"', w)
                w_index = md.well_name == w
                well = session.get_or_create(
                    tm.Well, plate_id=acquisition.plate.id, name=w
                )

                channel_image_files = list()
                for s in np.unique(md.loc[w_index, 'site']):
                    logger.debug('create site #%d', s)
                    s_index = md.site == s
                    y = md.loc[s_index, 'well_position_y'].values[0]
                    x = md.loc[s_index, 'well_position_x'].values[0]
                    height = md.loc[s_index, 'height'].values[0]
                    width = md.loc[s_index, 'width'].values[0]
                    site = session.get_or_create(
                        tm.Site, y=y, x=x, height=height, width=width,
                        well_id=well.id
                    )

                    for index, i in md.ix[s_index].iterrows():
                        channel_image_files.append(
                            tm.ChannelImageFile(
                                tpoint=i.tpoint, zplane=i.zplane,
                                channel_id=channels[i.channel_name],
                                site_id=site.id, acquisition_id=acquisition.id,
                                file_map=fmaps[index],
                            )
                        )

                session.bulk_save_objects(channel_image_files)

    def collect_job_output(self, batch):
        '''Assigns registered image files from different acquisitions to
        separate *cycles*. If an acquisition includes multiple time points,
        a separate *cycle* is created for each time point.
        The mapping from *acquisitions* to *cycles* is consequently
        1 -> n, where n is the number of time points per acquisition (n >= 1).

        Whether acquisition time points will be interpreted as actual
        time points in a time series depends on the value of
        :attr:`tm.Experiment.plate_acquisition_mode`.

        Parameters
        ----------
        batch: dict
            description of the *collect* job
        '''
        with tm.utils.ExperimentSession(self.experiment_id) as session:
            # We need to do this per plate to ensure correct indices
            # TODO: check plates have similar channels, etc
            experiment = session.query(tm.Experiment).one()
            acquisition_mode = experiment.plate_acquisition_mode
            logger.info('plates were acquired in mode "%s"', acquisition_mode)
            is_time_series = acquisition_mode == 'basic'
            if is_time_series:
                logger.info('time points are interpreted as time series')
            is_multiplexing = acquisition_mode == 'multiplexing'
            if is_multiplexing:
                logger.info('time points are interpreted as multiplexing cycles')

        with tm.utils.ExperimentSession(self.experiment_id) as session:

            channels = session.query(tm.Channel.name, tm.Channel.id).all()
            channel_lut = dict(channels)

            bit_depth = session.query(tm.Channel.bit_depth).distinct().one()
            if len(bit_depth) > 1:
                raise MetadataError('All channels must have the same bit depth.')
            bit_depth = bit_depth[0]
            wavelengths = session.query(tm.Channel.wavelength).\
                distinct().\
                all()
            wavelengths = [w[0] for w in wavelengths]

            # We order acquisitions by the time they got created. This will
            # determine the order of multiplexing cycles.
            plates = session.query(tm.Plate.id).\
                order_by(tm.Plate.created_at).\
                all()
            plate_ids = [p.id for p in plates]
            for p in plate_ids:
                acquisitions = session.query(tm.Acquisition.id).\
                    filter_by(plate_id=p).\
                    order_by(tm.Acquisition.created_at).\
                    all()
                acquisition_ids = [a.id for a in acquisitions]
                t_index = 0
                w_index = 0
                c_index = 0
                for a in acquisition_ids:
                    logger.debug('acquisition %d', a)
                    tpoints = session.query(tm.ChannelImageFile.tpoint).\
                        filter_by(acquisition_id=a).\
                        distinct().\
                        all()
                    tpoints = [t[0] for t in tpoints]
                    for t in tpoints:
                        logger.debug('time point #%d', t)
                        cycle = session.get_or_create(
                            tm.Cycle,
                            index=c_index, experiment_id=self.experiment_id
                        )

                        for w in wavelengths:
                            # Get all channel_image_files for the currently
                            # processed acquisition that match the old values
                            # of the "tpoint" and "channel_id" attributes.
                            image_files = session.query(tm.ChannelImageFile.id).\
                                filter_by(
                                    tpoint=t, acquisition_id=a,
                                    channel_id=channel_lut[w]
                                ).\
                                all()

                            if len(image_files) == 0:
                                # A wavelength might not have been used at
                                # every time point.
                                continue

                            logger.debug('wavelength "%s"', w)
                            if is_multiplexing:
                                # In case of a multiplexing experiment
                                # we create a separate channel for each
                                # combination of plate, wavelength and tpoint.
                                new_channel_name = '{p}_{c}_{w}'.format(
                                    p=p, c=c_index, w=w
                                )
                            else:
                                # In case of a time series experiment
                                # the name of the channel remains unchanged.
                                new_channel_name = w

                            # Check whether the channel already exists and
                            # update the name accordingly (upon creation, the
                            # "name" attribute should have been set to the
                            # value of the "wavelength" attribute).
                            channel = session.query(tm.Channel).\
                                filter_by(name=new_channel_name, wavelength=w).\
                                one_or_none()
                            if channel is not None:
                                channel.name = new_channel_name
                                session.add(channel)
                                session.commit()
                            else:
                                channel = tm.Channel(
                                    name=new_channel_name, wavelength=w,
                                    bit_depth=bit_depth,
                                    experiment_id=self.experiment_id
                                )
                                session.add(channel)
                                session.commit()

                            logger.info(
                                'update time point and channel id '
                                'of channel image files: tpoint=%d, channel=%s',
                                t_index, channel.name
                            )
                            # Update the attributes of channel_image_files with
                            # the new values for tpoint and channel_id and also
                            # add the cycle_id.
                            session.bulk_update_mappings(
                                tm.ChannelImageFile, [
                                  {
                                    'id': f.id,
                                    'tpoint': t_index,
                                    'cycle_id': cycle.id,
                                    'channel_id': channel.id
                                  } for f in image_files
                                ]
                            )

                            # Update lookup table
                            channel_lut[new_channel_name] = channel.id

                        if is_time_series:
                            t_index += 1
                        else:
                            c_index += 1
