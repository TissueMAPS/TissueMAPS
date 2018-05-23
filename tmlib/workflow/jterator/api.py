# TmLibrary - TissueMAPS library for distibuted image analysis routines.
# Copyright (C) 2016, 2018  University of Zurich
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
import re
import sys
import shutil
import logging
import subprocess
import numpy as np
import pandas as pd
import collections
import shapely.geometry
import shapely.ops
from cached_property import cached_property
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import FLOAT
from psycopg2 import ProgrammingError
from psycopg2.extras import Json
from gc3libs.quantity import Duration, Memory

import tmlib.models as tm
from tmlib.utils import autocreate_directory_property
from tmlib.utils import flatten
from tmlib.readers import TextReader
from tmlib.readers import ImageReader
from tmlib.writers import TextWriter
from tmlib.models.types import ST_GeomFromText
from tmlib.workflow.api import WorkflowStepAPI
from tmlib.errors import PipelineDescriptionError
from tmlib.errors import JobDescriptionError
from tmlib.workflow.jterator.project import Project, AvailableModules
from tmlib.workflow.jterator.module import ImageAnalysisModule
from tmlib.workflow.jterator.handles import SegmentedObjects
from tmlib.workflow.jobs import SingleRunPhase
from tmlib.workflow.jterator.jobs import DebugRunJob
from tmlib.workflow import register_step_api
from tmlib import cfg

logger = logging.getLogger(__name__)


@register_step_api('jterator')
class ImageAnalysisPipelineEngine(WorkflowStepAPI):

    '''Class for running image analysis pipelines.'''

    def __init__(self, experiment_id, pipeline_description=None,
            handles_descriptions=None):
        '''
        Parameters
        ----------
        experiment_id: int
            ID of the processed experiment
        pipeline_description: tmlib.workflow.jterator.description.PipelineDescription, optional
            description of pipeline, i.e. module order and paths to module
            source code and descriptor files (default: ``None``)
        handles_descriptions: Dict[str, tmlib.workflow.jterator.description.HandleDescriptions], optional
            description of module input/output (default: ``None``)

        Note
        ----
        If `pipe` or `handles` are not provided
        they are obtained from the persisted YAML descriptor files on disk.
        '''
        super(ImageAnalysisPipelineEngine, self).__init__(experiment_id)
        self._engines = {'Python': None, 'R': None}
        self.project = Project(
            location=self.step_location,
            pipeline_description=pipeline_description,
            handles_descriptions=handles_descriptions
        )

    @autocreate_directory_property
    def figures_location(self):
        '''str: location where figure files are stored'''
        return os.path.join(self.step_location, 'figures')

    def remove_previous_pipeline_output(self):
        '''Removes all figure files.'''
        shutil.rmtree(self.figures_location)
        os.mkdir(self.figures_location)

    @cached_property
    def pipeline(self):
        '''List[tmlib.jterator.module.ImageAnalysisModule]:
        pipeline built based on
        :class`PipelineDescription <tmlib.workflow.jterator.description.PipelineDescription>` and
        :class:`HandleDescriptions <tmlib.workflow.jterator.description.HandleDescriptions>`.
        '''
        handles = self.project.handles  # only compute this once
        pipeline = list()
        for i, element in enumerate(self.project.pipe.description.pipeline):
            if not element.active:
                continue
            if '/' in element.source:
                logger.debug('assuming module `%s` resides outside the configured module path', element.source)
                source_file = os.path.expanduser(os.path.expandvars(element.source))
                if not os.path.isabs(source_file):
                    source_file = os.path.join(self.step_location, source_file)
            else:
                logger.debug('searching for module `%s` in configured module path %r ...', element.source, cfg.modules_path)
                source_file = AvailableModules().find_module_by_name(element.source)
            if not os.path.exists(source_file):
                raise PipelineDescriptionError(
                    'Module source `{0}` resolved to non-existing file `{1}`'
                    .format(element.source, source_file))
            pipeline.append(
                ImageAnalysisModule(
                    name=handles[i].name,
                    source_file=source_file,
                    handles=handles[i].description
            ))
        return pipeline

    def start_engines(self):
        '''Starts engines required by non-Python modules in the pipeline.
        This should be done only once, since engines may have long startup
        times, which would otherwise slow down the execution of the pipeline.

        Note
        ----
        For Matlab, you need to set the MATLABPATH environment variable
        in order to add module dependencies to the Matlab path.

        Warning
        -------
        Matlab will be started with the ``"-nojvm"`` option.
        '''
        # TODO: JVM for java code
        languages = [m.language for m in self.pipeline]
        if 'Matlab' in languages:
            logger.info('start Matlab engine')
            try:
                import matlab_wrapper as matlab
            except ImportError:
                raise ImportError(
                    'Matlab engine cannot be started, because '
                    '"matlab-wrapper" package is not installed.'
                )
            # NOTE: It is absolutely necessary to specify these startup options
            # for use parallel processing on the cluster. Otherwise some jobs
            # hang up and get killed due to timeout.
            startup_ops = '-nosplash -singleCompThread -nojvm -nosoftwareopengl'
            logger.debug('Matlab startup options: %s', startup_ops)
            self._engines['Matlab'] = matlab.MatlabSession(options=startup_ops)
            # We have to make sure that code which may be called by a module,
            # are actually on the MATLAB path.
            # To this end, the MATLABPATH environment variable can be used.
            # However, this only adds the folder specified
            # by the environment variable, but not its subfolders. To enable
            # this, we add each directory specified in the environment variable
            # to the path.
            matlab_path = os.environ['MATLABPATH']
            matlab_path = matlab_path.split(':')
            for p in matlab_path:
                if not p:
                    continue
                logger.debug('add "%s" to MATLABPATH', p)
                self._engines['Matlab'].eval(
                    'addpath(genpath(\'{0}\'));'.format(p)
                )
        # if 'Julia' in languages:
        #     print 'jt - Starting Julia engine'
        #     self._engines['Julia'] = julia.Julia()

    def create_run_batches(self, args):
        '''Creates job descriptions for parallel computing.

        Parameters
        ----------
        args: tmlib.workflow.jterator.args.BatchArguments
            step-specific arguments

        Returns
        -------
        generator
            job descriptions
        '''
        channel_names = [
            ch.name for ch in self.project.pipe.description.input.channels
        ]

        if args.plot and args.batch_size != 1:
            raise JobDescriptionError(
                'Batch size must be 1 when plotting is active.'
            )

        with tm.utils.ExperimentSession(self.experiment_id) as session:
            # Distribute sites randomly. Thereby we achieve a certain level
            # of load balancing in case wells have different number of cells,
            # for example.
            sites = session.query(tm.Site.id).order_by(func.random()).all()
            site_ids = [s.id for s in sites]
            batches = self._create_batches(site_ids, args.batch_size)
            for j, batch in enumerate(batches):
                image_file_locations = session.query(
                        tm.ChannelImageFile._location
                    ).\
                    join(tm.Channel).\
                    filter(tm.Channel.name.in_(channel_names)).\
                    filter(tm.ChannelImageFile.site_id.in_(batch)).\
                    all()
                yield {
                    'id': j + 1,  # job IDs are one-based!
                    'site_ids': batch,
                    'plot': args.plot
                }

    def delete_previous_job_output(self):
        '''Deletes all instances of
        :class:`MapobjectType <tmlib.models.mapobject.MapobjectType>`
        that were generated by a prior run of the same pipeline as well as all
        children instances for the processed experiment.
        '''
        logger.info('delete existing mapobjects and mapobject types')
        with tm.utils.ExperimentSession(self.experiment_id, False) as session:
            static_types = ['Plates', 'Wells', 'Sites']
            mapobject_types = session.query(tm.MapobjectType.id).\
                filter(~tm.MapobjectType.name.in_(static_types)).\
                all()
            mapobject_type_ids = [t.id for t in mapobject_types]
            session.query(tm.Mapobject).\
                filter(tm.Mapobject.mapobject_type_id.in_(mapobject_type_ids)).\
                delete()
            session.query(tm.MapobjectType).\
                filter(tm.MapobjectType.id.in_(mapobject_type_ids)).\
                delete()

    def _load_pipeline_input(self, site_id):
        logger.info('load pipeline inputs')
        # Use an in-memory store for pipeline data and only insert outputs
        # into the database once the whole pipeline has completed successfully.
        store = {
            'site_id': site_id,
            'pipe': dict(),
            'current_figure': list(),
            'objects': dict(),
            'channels': list()
        }

        # Load the images, correct them if requested and align them if required.
        # NOTE: When the experiment was acquired in "multiplexing" mode,
        # images will be automatically aligned, assuming that this is the
        # desired behavior.
        channel_input = self.project.pipe.description.input.channels
        objects_input = self.project.pipe.description.input.objects
        with tm.utils.ExperimentSession(self.experiment_id) as session:
            site = session.query(tm.Site).get(site_id)
            y_offset, x_offset = site.aligned_offset
            height = site.aligned_height
            width = site.aligned_width

            for ch in channel_input:
                channel = session.query(
                        tm.Channel.bit_depth, tm.Channel.id
                    ).\
                    filter_by(name=ch.name).\
                    one()
                if channel.bit_depth == 16:
                    dtype = np.uint16
                elif channel.bit_depth == 8:
                    dtype = np.uint8

                records = session.query(tm.ChannelImageFile.tpoint).\
                    filter_by(site_id=site.id,channel_id=channel.id).\
                    distinct()
                tpoints = [r.tpoint for r in records]
                n_tpoints = len(tpoints)
                records = session.query(tm.ChannelImageFile.zplane).\
                    filter_by(site_id=site.id,channel_id=channel.id).\
                    distinct()
                zplanes = [r.zplane for r in records]
                n_zplanes = len(zplanes)

                image_array = np.zeros(
                    (height, width, n_zplanes, n_tpoints), dtype
                )
                if ch.correct:
                    logger.info(
                        'load illumination statistics for channel "%s"', ch.name
                    )
                    try:
                        stats_file = session.query(tm.IllumstatsFile).\
                            join(tm.Channel).\
                            filter(tm.Channel.name == ch.name).\
                            one()
                    except NoResultFound:
                        raise PipelineDescriptionError(
                            'No illumination statistics file found for '
                            'channel "%s"' % ch.name
                        )
                    stats = stats_file.get()
                else:
                    stats = None

                logger.info('load images for channel "%s"', ch.name)
                image_files = session.query(tm.ChannelImageFile).\
                    filter_by(site_id=site.id, channel_id=channel.id).\
                    all()
                for f in image_files:
                    logger.info('load image %d', f.id)
                    img = f.get()
                    if ch.correct:
                        logger.info('correct image %d', f.id)
                        img = img.correct(stats)
                    logger.debug('align image %d', f.id)
                    img = img.align()  # shifted and cropped!
                    image_array[:, :, f.zplane, f.tpoint] = img.array
                store['pipe'][ch.name] = image_array

            for obj in objects_input:
                mapobject_type = session.query(tm.MapobjectType).\
                    filter_by(name=obj.name).\
                    one()
                polygons = list()
                for t in sorted(tpoints):
                    zpolys = list()
                    for z in sorted(zplanes):
                        zpolys.append(
                            mapobject_type.get_segmentations_per_site(
                                site_id=site.id, tpoint=t, zplane=z
                            )
                        )
                    polygons.append(zpolys)

                segm_obj = SegmentedObjects(obj.name, obj.name)
                segm_obj.add_polygons(
                    polygons, y_offset, x_offset, (height, width)
                )
                store['objects'][segm_obj.name] = segm_obj
                store['pipe'][segm_obj.name] = segm_obj.value

        # Remove single-dimensions from image arrays.
        # NOTE: It would be more consistent to preserve shape, but most people
        # will work with 2D/3D images and having to deal with additional
        # dimensions would be rather annoying I assume.
        for name, img in store['pipe'].iteritems():
            store['pipe'][name] = np.squeeze(img)

        return store

    def _run_pipeline(self, store, site_id, plot=False):
        logger.info('run pipeline')
        for i, module in enumerate(self.pipeline):
            logger.info('run module "%s"', module.name)
            # When plotting is not deriberately activated it defaults to
            # headless mode
            module.update_handles(store, headless=not plot)
            module.run(self._engines[module.language])
            store = module.update_store(store)

            plotting_active = [
                h.value for h in module.handles.input if h.name == 'plot'
            ]
            if len(plotting_active) > 0:
                plotting_active = plotting_active[0]
            else:
                plotting_active = False
            if plot and plotting_active:
                figure_file = module.build_figure_filename(
                    self.figures_location, site_id
                )
                with TextWriter(figure_file) as f:
                    f.write(store['current_figure'])

        return store

    def _build_debug_run_command(self, site_id, verbosity):
        logger.debug('build "debug" command')
        command = [self.step_name]
        command.extend(['-v' for x in range(verbosity)])
        command.append(self.experiment_id)
        command.extend(['debug', '--site', str(site_id), '--plot'])
        return command

    def _save_pipeline_outputs(self, store, assume_clean_state):
        logger.info('save pipeline outputs')
        objects_output = self.project.pipe.description.output.objects
        for item in objects_output:
            as_polygons = item.as_polygons
            store['objects'][item.name].save = True
            store['objects'][item.name].represent_as_polygons = as_polygons

        with tm.utils.ExperimentSession(self.experiment_id, False) as session:
            layer = session.query(tm.ChannelLayer).first()
            mapobject_type_ids = dict()
            segmentation_layer_ids = dict()
            objects_to_save = dict()
            feature_ids = collections.defaultdict(dict)
            for obj_name, segm_objs in store['objects'].iteritems():
                if segm_objs.save:
                    logger.info('objects of type "%s" are saved', obj_name)
                    objects_to_save[obj_name] = segm_objs
                else:
                    logger.info('objects of type "%s" are not saved', obj_name)
                    continue
                logger.debug('add object type "%s"', obj_name)
                mapobject_type = session.get_or_create(
                    tm.MapobjectType, experiment_id=self.experiment_id,
                    name=obj_name, ref_type=tm.Site.__name__
                )
                mapobject_type_ids[obj_name] = mapobject_type.id
                # Create a feature values entry for each segmented object at
                # each time point.
                logger.info('add features for objects of type "%s"', obj_name)
                for feature_name in segm_objs.measurements[0].columns:
                    logger.debug('add feature "%s"', feature_name)
                    feature = session.get_or_create(
                        tm.Feature, name=feature_name,
                        mapobject_type_id=mapobject_type_ids[obj_name],
                        is_aggregate=False
                    )
                    feature_ids[obj_name][feature_name] = feature.id

                for (t, z), plane in segm_objs.iter_planes():
                    segmentation_layer = session.get_or_create(
                        tm.SegmentationLayer,
                        mapobject_type_id=mapobject_type.id,
                        tpoint=t, zplane=z
                    )

                    segmentation_layer_ids[(obj_name, t, z)] = \
                        segmentation_layer.id

            site = session.query(tm.Site).get(store['site_id'])
            y_offset, x_offset = site.aligned_offset

            mapobject_ids = dict()
            for obj_name, segm_objs in objects_to_save.iteritems():
                if not assume_clean_state:
                    # Delete existing mapobjects for this site, which were
                    # generated in a previous run of the same pipeline. In case
                    # they were passed as inputs don't delete them.
                    inputs = self.project.pipe.description.input.objects
                    if obj_name not in inputs:
                        logger.info(
                            'delete segmentations for existing mapobjects of '
                            'type "%s"', obj_name
                        )
                        session.query(tm.Mapobject).\
                            filter_by(
                                mapobject_type_id=mapobject_type_ids[obj_name],
                                partition_key=store['site_id']
                            ).\
                            delete()

                # Create a mapobject for each segmented object, i.e. each
                # pixel component having a unique label.
                logger.info('add objects of type "%s"', obj_name)
                # TODO: Can we avoid these multiple loops?
                # Is the bottleneck inserting objects into the db or Python?
                mapobjects = [
                    tm.Mapobject(
                        partition_key=store['site_id'],
                        mapobject_type_id=mapobject_type_ids[obj_name]
                    )
                    for _ in segm_objs.labels
                ]
                logger.info('insert objects into database')
                # FIXME: does this update the id attribute?
                session.bulk_ingest(mapobjects)
                session.flush()
                mapobject_ids = {
                    label: mapobjects[i].id
                    for i, label in enumerate(segm_objs.labels)
                }

                # Create a polygon and/or point for each segmented object
                # based on the cooridinates of their contours and centroids,
                # respectively.
                logger.info(
                    'add segmentations for objects of type "%s"', obj_name
                )
                mapobject_segmentations = list()
                if segm_objs.represent_as_polygons:
                    logger.debug('represent segmented objects as polygons')
                    iterator = segm_objs.iter_polygons(y_offset, x_offset)
                    for t, z, label, polygon in iterator:
                        logger.debug(
                            'add segmentation for object #%d at '
                            'tpoint %d and zplane %d', label, t, z
                        )
                        if polygon.is_empty:
                            logger.warn(
                                'object #%d of type %s doesn\'t have a polygon',
                                label, obj_name
                            )
                            # TODO: Shall we rather raise an Exception here???
                            # At the moment we remove the corresponding
                            # mapobjects in the collect phase.
                            continue
                        mapobject_segmentations.append(
                            tm.MapobjectSegmentation(
                                partition_key=store['site_id'], label=label,
                                geom_polygon=polygon,
                                geom_centroid=polygon.centroid,
                                mapobject_id=mapobject_ids[label],
                                segmentation_layer_id=segmentation_layer_ids[
                                    (obj_name, t, z)
                                ],
                            )
                        )
                else:
                    logger.debug('represent segmented objects only as points')
                    iterator = segm_objs.iter_points(y_offset, x_offset)
                    for t, z, label, centroid in iterator:
                        logger.debug(
                            'add segmentation for object #%d at '
                            'tpoint %d and zplane %d', label, t, z
                        )
                        mapobject_segmentations.append(
                            tm.MapobjectSegmentation(
                                partition_key=store['site_id'], label=label,
                                geom_polygon=None, geom_centroid=centroid,
                                mapobject_id=mapobject_ids[label],
                                segmentation_layer_id=segmentation_layer_ids[
                                    (obj_name, t, z)
                                ]
                            )
                        )
                logger.info('insert segmentations into database')
                session.bulk_ingest(mapobject_segmentations)

                logger.info(
                    'add feature values for objects of type "%s"', obj_name
                )
                logger.debug('round feature values to 6 decimals')
                feature_values = list()
                for t, data in enumerate(segm_objs.measurements):
                    data = data.round(6)  # single!
                    if data.empty:
                        logger.warn('empty measurement at time point %d', t)
                        continue
                    elif data.shape[0] < len(mapobject_ids):
                        # We clean up these objects in the collect phase.
                        logger.error('missing feature values')
                    elif data.shape[0] > len(mapobject_ids):
                        # Not sure this could happen.
                        logger.error('too many feature values')
                    column_lut = feature_ids[obj_name]
                    for label, c in data.rename(columns=column_lut).iterrows():
                        logger.debug(
                            'add values for mapobject #%d at time point %d',
                            label, t
                        )
                        values = dict(
                            zip(c.index.astype(str), c.values.astype(str))
                        )
                        feature_values.append(
                            tm.FeatureValues(
                                partition_key=store['site_id'],
                                mapobject_id=mapobject_ids[label],
                                tpoint=t, values=values
                            )
                        )
                logger.debug('insert feature values into db table')
                session.bulk_ingest(feature_values)

    def create_debug_run_phase(self, submission_id):
        '''Creates a job collection for the debug "run" phase of the step.

        Parameters
        ----------
        submission_id: int
            ID of the corresponding
            :class:`Submission <tmlib.models.submission.Submission>`

        Returns
        -------
        tmlib.workflow.job.RunPhase
            collection of debug "run" jobs
        '''
        return SingleRunPhase(
            step_name=self.step_name, submission_id=submission_id,
            parent_id=None
        )

    def create_debug_run_jobs(self, user_name, job_collection,
            batches, verbosity, duration, memory, cores):
        '''Creates debug jobs for the parallel "run" phase of the step.

        Parameters
        ----------
        user_name: str
            name of the submitting user
        job_collection: tmlib.workflow.job.RunPhase
            empty collection of *run* jobs that should be populated
        batches: List[dict]
            job descriptions
        verbosity: int
            logging verbosity for jobs
        duration: str
            computational time that should be allocated for a single job;
            in HH:MM:SS format
        memory: int
            amount of memory in Megabyte that should be allocated for a single
        cores: int
            number of CPU cores that should be allocated for a single job

        Returns
        -------
        tmlib.workflow.jobs.RunPhase
            run jobs
        '''
        logger.info(
            'create "debug" run jobs for submission %d',
            job_collection.submission_id
        )
        logger.debug('allocated time for debug run jobs: %s', duration)
        logger.debug('allocated memory for debug run jobs: %d MB', memory)
        logger.debug('allocated cores for debug run jobs: %d', cores)

        for b in batches:
            job = DebugRunJob(
                step_name=self.step_name,
                arguments=self._build_debug_run_command(b['site_id'], verbosity),
                output_dir=self.log_location,
                job_id=b['site_id'],
                submission_id=job_collection.submission_id,
                parent_id=job_collection.persistent_id,
                user_name=user_name
            )
            job.requested_walltime = Duration(duration)
            job.requested_memory = Memory(memory, Memory.MB)
            if not isinstance(cores, int):
                raise TypeError(
                    'Argument "cores" must have type int.'
                )
            if not cores > 0:
                raise ValueError(
                    'The value of "cores" must be positive.'
                )
            job.requested_cores = cores
            job_collection.add(job)
        return job_collection

    def run_job(self, batch, assume_clean_state):
        '''Runs the pipeline, i.e. executes modules sequentially. After
        successful completion of the pipeline, instances of
        :class:`MapobjectType <tmlib.models.mapobject.MapobjectType>`,
        :class:`Mapobject <tmlib.models.mapobject.Mapobject>`,
        :class:`SegmentationLayer <tmlib.models.layer.SegmentationLayer>`,
        :class:`MapobjectSegmentation <tmlib.models.mapobject.MapobjectSegmentation>`,
        :class:`Feature <tmlib.models.feature.Feature>` and
        :class:`FeatureValues <tmlib.models.feature.FeatureValues>`
        are created and persisted in the database for subsequent
        visualization and analysis.

        Parameters
        ----------
        batch: dict
            job description
        assume_clean_state: bool, optional
            assume that output of previous runs has already been cleaned up
        '''
        logger.info('handle pipeline input')

        self.start_engines()

        # Enable debugging of pipelines by providing the full path to images.
        # This requires a work around for "plot" and "job_id" arguments.
        for site_id in batch['site_ids']:
            logger.info('process site %d', site_id)
            store = self._load_pipeline_input(site_id)
            store = self._run_pipeline(store, site_id, batch['plot'])
            self._save_pipeline_outputs(store, assume_clean_state)

    def collect_job_output(self, batch):
        '''Computes the optimal representation of each
        :class:`SegmentationLayer <tmlib.models.layer.SegmentationLayer>` on the
        map for zoomable visualization.

        Parameters
        ----------
        batch: dict
            job description
        '''

        logger.info('compute zoom level thresholds for mapobjects')
        with tm.utils.ExperimentSession(self.experiment_id, False) as session:
            experiment = session.query(tm.Experiment.pyramid_depth).one()
            maxzoom = experiment.pyramid_depth - 1
            segmentation_layers = session.query(tm.SegmentationLayer).all()
            polygon_representation_lut = {
                o.name: o.as_polygons
                for o in self.project.pipe.description.output.objects
            }
            segmented_mapobject_types = list()
            for layer in segmentation_layers:
                mapobject_type_name = layer.mapobject_type.name
                as_polygons = polygon_representation_lut.get(
                    mapobject_type_name, True
                )
                pt, ct = layer.calculate_zoom_thresholds(maxzoom, as_polygons)
                layer.polygon_thresh = pt
                layer.centroid_thresh = ct
                session.flush()
                if (layer.tpoint is not None and
                        layer.zplane is not None):
                    segmented_mapobject_types.append(layer.mapobject_type)

            logger.info(
                'clean-up mapobjects with invalid or missing segmentations '
                'or missing feature values'
            )
            # DELETE queries with complex WHERE clauses are not supported
            # for distributed tables. We therefore need to determine the ids
            # of mapobjects first and then use a simple WHERE clause with ANY.
            for mapobject_type in segmented_mapobject_types:
                mapobjects = session.query(tm.Mapobject.id).\
                    outerjoin(tm.MapobjectSegmentation).\
                    filter(
                        tm.MapobjectSegmentation.mapobject_id == None,
                        tm.Mapobject.mapobject_type_id == mapobject_type.id
                    ).\
                    all()
                mapobjects += session.query(tm.Mapobject.id).\
                    outerjoin(tm.MapobjectSegmentation).\
                    filter(
                        ~tm.MapobjectSegmentation.geom_polygon.ST_IsValid(),
                        tm.Mapobject.mapobject_type_id == mapobject_type.id
                    ).\
                    all()
                # When checking for objects with  missing feature values, we
                # need to make sure that the mapobject type has any features
                # at all, otherwise all mapobjects would get deleted when
                # applying this logic.
                if len(mapobject_type.features) > 0:
                    mapobjects += session.query(tm.Mapobject.id).\
                        outerjoin(tm.FeatureValues).\
                        filter(
                            tm.FeatureValues.mapobject_id == None,
                            tm.Mapobject.mapobject_type_id == mapobject_type.id
                        ).\
                        all()
                mapobject_ids = [m.id for m in mapobjects]
                session.query(tm.Mapobject).\
                    filter(tm.Mapobject.id.in_(mapobject_ids)).\
                    delete()

    @staticmethod
    def _add_feature(conn, name, mapobject_type_id, is_aggregate):
        conn.execute('''
            INSERT INTO features (name, is_aggregate, mapobject_type_id)
            VALUES (%(name)s, %(is_aggregate)s, %(mapobject_type_id)s)
            ON CONFLICT
            ON CONSTRAINT features_name_mapobject_type_id_key
            DO NOTHING
            RETURNING id
        ''', {
            'name': name,
            'is_aggregate': is_aggregate,
            'mapobject_type_id': mapobject_type_id
        })
        record = conn.fetchone()
        if record is None:
            conn.execute('''
                SELECT id FROM features
                WHERE name = %(name)s
                AND mapobject_type_id = %(mapobject_type_id)s
            ''', {
                'name': name,
                'mapobject_type_id': mapobject_type_id
            })
            record = conn.fetchone()
        return record.id
