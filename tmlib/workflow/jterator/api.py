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
import sys
import shutil
import logging
import json
import subprocess
import numpy as np
import pandas as pd
import collections
import shapely.geometry
import shapely.ops
import matlab_wrapper as matlab
from cached_property import cached_property
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.sql import func
from psycopg2 import ProgrammingError
from psycopg2.extras import Json

import tmlib.models as tm
from tmlib.utils import autocreate_directory_property
from tmlib.utils import flatten
from tmlib.readers import TextReader
from tmlib.readers import ImageReader
from tmlib.writers import TextWriter
from tmlib.workflow.api import ClusterRoutines
from tmlib.errors import PipelineDescriptionError
from tmlib.errors import JobDescriptionError
from tmlib.log import map_logging_verbosity
from tmlib.workflow.jterator.utils import complete_path
from tmlib.workflow.jterator.utils import get_module_path
from tmlib.workflow.jterator.project import Project
from tmlib.workflow.jterator.module import ImageAnalysisModule
from tmlib.workflow.jterator.handles import SegmentedObjects
from tmlib.workflow.jterator.checkers import PipelineChecker
from tmlib.workflow import register_step_api
from tmlib.models.mapobject import (
    delete_mapobject_types_cascade, delete_mapobjects_cascade,
    delete_invalid_mapobjects_cascade
)
from tmlib.models.feature import delete_features_cascade
from tmlib import cfg

logger = logging.getLogger(__name__)


@register_step_api('jterator')
class ImageAnalysisPipeline(ClusterRoutines):

    '''Class for running image processing pipelines.'''

    def __init__(self, experiment_id, verbosity, pipeline,
            pipe=None, handles=None):
        '''
        Parameters
        ----------
        experiment_id: int
            ID of the processed experiment
        verbosity: int
            logging level
        pipeline: str
            name of the pipeline that should be processed
        pipe: dict, optional
            description of pipeline, i.e. module order and paths to module
            source code and descriptor files (default: ``None``)
        handles: List[dict], optional
            description of module input/output (default: ``None``)

        Note
        ----
        If `pipe` or `handles` are not provided
        they are obtained from the YAML *.pipe* and *.handle* descriptor
        files on disk.
        '''
        super(ImageAnalysisPipeline, self).__init__(experiment_id, verbosity)
        self.engines = {'Python': None, 'R': None}
        self.name = pipeline
        self.project = Project(
            step_location=self.step_location, name=pipeline,
            pipe=pipe, handles=handles
        )

    @autocreate_directory_property
    def step_location(self):
        '''str: directory where files for job description, pipeline and module
        description, log output, and figures are stored
        '''
        step_location = os.path.join(self.workflow_location, self.step_name)
        if not os.path.exists(step_location):
            os.mkdir(step_location)
        return os.path.join(step_location, self.name)

    def check_pipeline(self):
        '''Checks descriptions provided via `pipe` and `handles` files.
        '''
        handles_descriptions = [h['description'] for h in self.project.handles]
        checker = PipelineChecker(
            step_location=self.step_location,
            pipe_description=self.project.pipe['description'],
            handles_descriptions=handles_descriptions
        )
        checker.check_all()

    @autocreate_directory_property
    def figures_location(self):
        '''str: location where figure files are stored
        '''
        return os.path.join(self.step_location, 'figures')

    def remove_previous_pipeline_output(self):
        '''Removes all figure and module log files.'''
        shutil.rmtree(self.figures_location)
        os.mkdir(self.figures_location)

    @cached_property
    def pipeline(self):
        '''List[tmlib.jterator.module.JtModule]: pipeline built in modular form
        based on `pipe` and `handles` descriptions

        Raises
        ------
        tmlib.errors.PipelineDescriptionError
            when information in *pipe* description is missing or incorrect
        OSError
            when environment variable "TMAPS_MODULES_HOME" would be required but doesn't
            exist
        '''
        libpath = cfg.modules_home
        # libpath = self.project.pipe['description'].get('lib', None)
        # libpath = complete_path(libpath, self.step_location)
        pipeline = list()
        for i, element in enumerate(self.project.pipe['description']['pipeline']):
            if not element['active']:
                continue
            module_filename = element['source']
            source_path = get_module_path(module_filename, libpath)
            if not os.path.exists(source_path):
                raise PipelineDescriptionError(
                    'Module file does not exist: %s' % source_path
                )
            name = self.project.handles[i]['name']
            description = self.project.handles[i]['description']
            module = ImageAnalysisModule(
                name=name, source_file=source_path, description=description
            )
            pipeline.append(module)
        # if not pipeline:
        #     raise PipelineDescriptionError('No pipeline description available')
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
            # NOTE: It is absolutely necessary to specify these startup options
            # for use parallel processing on the cluster. Otherwise some jobs
            # hang up and get killed due to timeout.
            startup_ops = '-nosplash -singleCompThread -nojvm -nosoftwareopengl'
            logger.debug('Matlab startup options: %s', startup_ops)
            self.engines['Matlab'] = matlab.MatlabSession(options=startup_ops)
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
                self.engines['Matlab'].eval(
                    'addpath(genpath(\'{0}\'));'.format(p)
                )
        # if 'Julia' in languages:
        #     print 'jt - Starting Julia engine'
        #     self.engines['Julia'] = julia.Julia()

    def _configure_loggers(self):
        # TODO: configure loggers for Python, Matlab, and R modules
        level = map_logging_verbosity(self.verbosity)
        jtlib_logger = logging.getLogger('jtlib')
        jtlib_logger.setLevel(level)
        jtmodules_logger = logging.getLogger('jtmodules')
        jtmodules_logger.setLevel(level)

    def create_batches(self, args, job_ids=None):
        '''Creates job descriptions for parallel computing.

        Parameters
        ----------
        args: tmlib.workflow.jterator.args.BatchArguments
            step-specific arguments
        job_ids: Set[int], optional
            subset of jobs for which descriptions should be generated
            (default: ``None``)

        Returns
        -------
        Dict[str, List[dict] or dict]
            job descriptions
        '''
        job_descriptions = dict()
        job_descriptions['run'] = list()
        self.check_pipeline()

        channel_names = [
            ch['name']
            for ch in self.project.pipe['description']['input']['channels']
        ]

        if args.plot and args.batch_size != 1:
            raise JobDescriptionError(
                'Batch size must be 1 when plotting is active.'
            )

        # TODO: parallelize over sub-regions in the image
        # region = self.project.pipe['description']['input']['region']
        # overlap = self.project.pipe['description']['input']['overlap']

        with tm.utils.ExperimentSession(self.experiment_id) as session:

            sites = session.query(tm.Site.id).all()
            site_ids = [s.id for s in sites]

            batches = self._create_batches(site_ids, args.batch_size)
            if job_ids is None:
                job_ids = set(range(1, len(batches)+1))

            for j, batch in enumerate(batches):

                job_id = j+1  # job IDs are one-based!

                if job_id not in job_ids:
                    continue

                image_file_locations = session.query(
                        tm.ChannelImageFile._location
                    ).\
                    join(tm.Channel).\
                    filter(tm.Channel.name.in_(channel_names)).\
                    filter(tm.ChannelImageFile.site_id.in_(batch)).\
                    all()

                job_descriptions['run'].append({
                    'id': job_id,
                    'inputs': {
                        'image_files': [f[0] for f in image_file_locations]
                    },
                    'outputs': {},
                    'site_ids': batch,
                    'plot': args.plot,
                    'debug': False
                })

        job_descriptions['collect'] = {
            'inputs': dict(),
            'outputs': dict()
        }

        return job_descriptions

    def delete_previous_job_output(self):
        '''Deletes all instances of
        :class:`MapobjectType <tmlib.models.mapobject.MapobjectType>`
        that were generated by a prior run of the same pipeline as well as all
        children instances for the processed experiment.
        '''
        logger.info('delete existing mapobjects and mapobject types')
        delete_mapobject_types_cascade(self.experiment_id)

    def _build_run_command(self, job_id):
        # Overwrite method to include "--pipeline" argument
        command = [self.step_name]
        command.extend(['-v' for x in xrange(self.verbosity)])
        # Pipeline name may include spaces
        command.extend(['--pipeline', self.project.name])
        command.append(self.experiment_id)
        command.extend(['run', '--job', str(job_id)])
        return command

    def _build_collect_command(self):
        # Overwrite method to include "--pipeline" argument
        command = [self.step_name]
        command.extend(['-v' for x in xrange(self.verbosity)])
        command.extend(['--pipeline', self.project.name])
        command.append(self.experiment_id)
        command.append('collect')
        return command

    def _load_pipeline_inputs(self, site_id, debug=False):
        logger.info('load pipeline inputs')
        # Use an in-memory store for pipeline data and only insert outputs
        # into the database once the whole pipeline has completed successfully.
        store = {
            'site_id': site_id,
            'pipe': dict(),
            'current_figure': list(),
            'segmented_objects': dict(),
            'channels': list()
        }

        # Load the images, correct them if requested and align them if required.
        # NOTE: When the experiment was acquired in "multiplexing" mode,
        # images will be automatically aligned, assuming that this is the
        # desired behavior.
        channel_input = self.project.pipe['description']['input'].get(
            'channels', list()
        )
        mapobject_type_info = self.project.pipe['description']['input'].get(
            'mapobject_types', list()
        )
        mapobject_type_names = [mt['name'] for mt in mapobject_type_info]
        with tm.utils.ExperimentSession(self.experiment_id) as session:
            for item in channel_input:
                # NOTE: When "path" key is present, the image is loaded from
                # a file on disk. The image is not further processed, such as
                # corrected for illuminatiion artifacts or aligned.
                images = collections.defaultdict(list)
                if debug:
                    path = item.get('path', None)
                    if path is None:
                        raise JobDescriptionError(
                            'Input items require key "path" in debug mode.'
                        )
                    logger.info(
                        'load image for channel "%s" from file: %s',
                        item['name'], path
                    )
                    with ImageReader(path) as f:
                        array = f.read()
                    images = {0: array}
                else:
                    site = session.query(tm.Site).get(site_id)
                    if item['correct']:
                        logger.info('load illumination statistics')
                        try:
                            stats_file = session.query(tm.IllumstatsFile).\
                                join(tm.Channel).\
                                join(tm.Cycle).\
                                filter(tm.Channel.name == item['name']).\
                                filter(tm.Cycle.plate_id == site.well.plate_id).\
                                one()
                        except NoResultFound:
                            raise PipelineDescriptionError(
                                'No illumination statistics file found for '
                                'channel "%s"' % item['name']
                            )
                        stats = stats_file.get()

                    logger.info('load images for channel "%s"', item['name'])
                    image_files = session.query(tm.ChannelImageFile).\
                        join(tm.Channel).\
                        filter(
                            tm.Channel.name == item['name'],
                            tm.ChannelImageFile.site_id == site.id
                        ).\
                        all()

                    for f in image_files:
                        logger.info('load image %d', f.id)
                        img = f.get()
                        if item['correct']:
                            logger.info('correct image %d', f.id)
                            img = img.correct(stats)
                        logger.debug('align image %d', f.id)
                        img = img.align()  # shifted and cropped!
                        images[f.tpoint].append(img.array)

                store['pipe'][item['name']] = np.stack(images.values(), axis=-1)

            # Load outlins of mapobjects of the specified types and reconstruct
            # the label images required by modules.
            if not debug:
                for mapobject_type_name in mapobject_type_names:
                    mapobject_type = session.query(tm.MapobjectType.id).\
                        filter_by(name=mapobject_type_name).\
                        one()
                    segmentations = session.query(
                            tm.MapobjectSegmentation.tpoint,
                            tm.MapobjectSegmentation.zplane,
                            tm.MapobjectSegmentation.label,
                            tm.MapobjectSegmentation.geom_poly
                        ).\
                        join(
                            tm.Mapobject,
                            tm.Mapobject.id == tm.MapojbectSegmentation.mapobject_id
                        ).\
                        filter(
                            tm.Mapobject.mapobject_type_id == mapobject_type.id,
                            tm.MapobjectSegmentation.site_id == site_id
                        ).\
                        all()
                    dims = store['pipe'].values()[0].shape
                    # Add the labeled image to the pipeline and create a handle
                    # object to later add measurements for the objects.
                    handle = SegmentedObjects(
                        name=mapobject_type_name, key=mapobject_type_name
                    )
                    polygons = {
                        (s.tpoint, s.zplane, s.label): s.geom_poly
                        for s in segmentations
                    }
                    # The polygon coordinates are global, i.e. relative to the
                    # map overview. Therefore we have to provide the offsets
                    # for each axis.
                    site = session.query(tm.Site).get(site_id)
                    y_offset, x_offset = site.offset
                    y_offset += site.intersection.lower_overhang
                    x_offset += site.intersection.right_overhang
                    handle.from_polygons(polygons, y_offset, x_offset, dims)
                    store['pipe'][handle.key] = handle.value
                    store['segmented_objects'][handle.key] = handle

        # Remove single-dimensions from image arrays.
        # NOTE: It would be more consistent to preserve shape, but most people
        # will work with 2D/3D images and having to deal with additional
        # dimensions would be rather annoying I assume.
        for name, img in store['pipe'].iteritems():
            store['pipe'][name] = np.squeeze(img)

        return store

    def _run_pipeline(self, store, job_id, plot=False):
        logger.info('run pipeline')
        for i, module in enumerate(self.pipeline):
            logger.info('run module "%s"', module.name)
            # When plotting is not deriberately activated it defaults to
            # headless mode
            module.instantiate_handles()
            module.update_handles(store, headless=not plot)
            module.run(self.engines[module.language])
            store = module.update_store(store)

            plotting_active = [
                h.value for h in module.handles['input'] if h.name == 'plot'
            ]
            if len(plotting_active) > 0:
                plotting_active = plotting_active[0]
            else:
                plotting_active = False
            if plot and plotting_active:
                figure_file = module.build_figure_filename(
                    self.figures_location, job_id
                )
                with TextWriter(figure_file) as f:
                    f.write(store['current_figure'])

        return store

    def _save_pipeline_outputs(self, store):
        logger.info('save pipeline outputs')
        with tm.utils.ExperimentSession(self.experiment_id) as session:
            layer = session.query(tm.ChannelLayer).first()
            mapobject_type_ids = dict()
            for obj_name, segm_objs in store['segmented_objects'].iteritems():
                logger.debug('add mapobject type "%s"', obj_name)
                mapobject_type = session.get_or_create(
                    tm.MapobjectType, name=obj_name
                )
                mapobject_type_ids[obj_name] = mapobject_type.id
                # We will update this in collect phase, but we need to set some
                # limits in case the user already starts viewing objects on the
                # map. Without any contraints the user interface might explode.
                min_poly_zoom = layer.maxzoom_level_index - 3
                mapobject_type.min_poly_zoom = \
                    0 if min_poly_zoom < 0 else min_poly_zoom
                max_poly_zoom = mapobject_type.min_poly_zoom - 2
                mapobject_type.max_poly_zoom = \
                    0 if max_poly_zoom < 0 else max_poly_zoom

            site = session.query(tm.Site).get(store['site_id'])
            y_offset, x_offset = site.offset
            if site.intersection is not None:
                y_offset += site.intersection.lower_overhang
                x_offset += site.intersection.right_overhang

        with tm.utils.ExperimentConnection(self.experiment_id) as conn:
            mapobject_ids = dict()
            for obj_name, segm_objs in store['segmented_objects'].iteritems():
                # Delete existing mapobjects for this site when they were
                # generated in a previous run of the same pipeline. In case
                # they were passed to the pipeline as inputs don't delete them
                # because this means they were generated by another pipeline.
                inputs = self.project.pipe['description']['input'].get(
                    'mapobject_types', list()
                )
                if obj_name not in inputs:
                    logger.info(
                        'delete segmentations for existing mapobjects of '
                        'type "%s"', obj_name
                    )
                    delete_mapobjects_cascade(
                        self.experiment_id,
                        mapobject_type_ids=[mapobject_type_ids[obj_name]],
                        site_id=store['site_id'], pipeline=self.project.name
                    )

        with tm.utils.ExperimentConnection(self.experiment_id) as conn:
            for obj_name, segm_objs in store['segmented_objects'].iteritems():
                logger.info('create objects of type "%s"', obj_name)

                # Get existing mapobjects for this site in case they were
                # created by a previous pipeline or create new mapobjects in
                # case they didn't exist (or got just deleted).
                mapobject_ids = dict()
                for label in segm_objs.labels:
                    logger.debug('create object #%d', label)
                    mapobject_ids[label] = self._add_mapobject(
                        conn, mapobject_type_ids[obj_name]
                    )

                # Save segmentations, i.e. create a polygon for each
                # segmented object based on the cooridinates of their
                # contours.
                logger.debug('create segmentations for object #%d', label)
                border_indices = segm_objs.is_border
                polygons = segm_objs.to_polygons(y_offset, x_offset)
                for (t, z, label), polygon in polygons.iteritems():
                    logger.debug(
                        'create segmentation for tpoint %d and zplane %d', t, z
                    )
                    if polygon.is_empty:
                        logger.warn(
                            'object #%d of type %s doesn\'t have a polygon',
                            label, obj_name
                        )
                        continue
                    self._add_mapobject_segmentation(
                        conn, mapobject_ids[label], polygon, t, z,
                        store['site_id'], bool(border_indices[t][label]),
                        self.project.name
                    )

                logger.info(
                    'add features for objects of type "%s"', obj_name
                )
                feature_ids = dict()
                for fname in segm_objs.measurements[0].columns:
                    logger.debug('add feature "%s"', fname)
                    feature_ids[fname] = self._add_feature(
                        conn, fname, mapobject_type_ids[obj_name], False
                    )

                for t, data in enumerate(segm_objs.measurements):
                    if data.empty:
                        logger.warn('empty measurement at time point %d', t)
                        continue
                    for label, vals in data.rename(columns=feature_ids).iterrows():
                        logger.info(
                            'add values for object #%d at time point %d',
                            label, t
                        )
                        self._add_feature_values(
                            conn, dict(vals), mapobject_ids[label], t
                        )

    def run_job(self, batch):
        '''Runs the pipeline, i.e. executes modules sequentially. After
        successful completion of the pipeline,
        :class:`MapobjectType <tmlib.models.mapobject.MapobjectType>`,
        :class:`Mapobject <tmlib.models.mapobject.Mapobject>` and
        :class:`MapobjectSegmentation <tmlib.models.mapobject.MapobjectSegmentation>`
        as well as each extracted :class:`Feature <tmlib.models.feature.Feature>`
        and the :class:`FeatureValue <tmlib.models.feature.FeatureValue>`
        for each segmented object are written into the database and are
        available for display and analysis in the viewer.

        Parameters
        ----------
        batch: dict
            job description
        '''
        logger.info('handle pipeline input')
        checker = PipelineChecker(
            step_location=self.step_location,
            pipe_description=self.project.pipe['description'],
            handles_descriptions=[
                h['description'] for h in self.project.handles
            ]
        )
        checker.check_all()
        self._configure_loggers()

        self.start_engines()

        # Enable debugging of pipelines by providing the full path to images.
        # This requires a work around for "plot" and "job_id" arguments.
        if batch['debug']:
            site_ids = [None]
            plot = False
            job_id = None
        else:
            site_ids = batch['site_ids']
            plot = batch.get('plot')
            job_id = batch.get('id')

        for sid in site_ids:
            logger.info('process site %d', sid)
            # Load inputs
            store = self._load_pipeline_inputs(sid, batch['debug'])
            # Run pipeline
            store = self._run_pipeline(store, job_id, plot)
            # Write output
            if batch['debug']:
                logger.info('debug mode: no output written')
                sys.exit(0)
            else:
                self._save_pipeline_outputs(store)

    def collect_job_output(self, batch):
        '''Creates :class:`MapobjectType <tmlib.models.mapobject.MapobjectType>`
        instances for :class:`Site <tmlib.models.site.Site>`,
        :class:`Well <tmlib.models.well.Well>`,
        and :class:`Plate <tmlib.models.plate.Plate>`
        and creates for each object an instance of
        :class:`Mapobject <tmlib.models.mapobject.Mapobject>`
        as well as the corresponding
        :class:`MapobjectSegmentation <tmlib.models.mapobject.MapobjectSegmentation>`.
        It further computes aggregate features over intersecting child mapobjects,
        e.g. the number of cells within a well.

        Parameters
        ----------
        batch: dict
            job description
        '''
        logger.info('clean-up mapobjects with invalid segmentations')
        delete_invalid_mapobjects_cascade(self.experiment_id)

        logger.info(
            'calculate minimal/maximal zoom level for representation of '
            'mapobjects as polygons or points'
        )
        with tm.utils.ExperimentSession(self.experiment_id) as session:
            layer = session.query(tm.ChannelLayer).first()
            mapobject_types = session.query(tm.MapobjectType).\
                filter_by(is_static=False)

            maxzoom = layer.maxzoom_level_index
            for mapobject_type in mapobject_types:
                min_zoom, max_zoom = mapobject_type.calculate_min_max_poly_zoom(
                    maxzoom
                )
                logger.info(
                    'zoom level for mapobjects of type "%s": %d',
                    mapobject_type.name, min_poly_zoom
                )
                mapobject_type.min_poly_zoom = min_zoom
                mapobject_type.max_poly_zoom = max_zoom

        with tm.utils.ExperimentSession(self.experiment_id) as session:
            # For now, calculate moments only for "static" mapobjects,
            # such as "Wells" or "Sites"
            mapobject_mappings = {
                'Plate': session.query(tm.Plate),
                'Wells': session.query(tm.Well),
                'Sites': session.query(tm.Site)
            }
            logger.info('delete existing aggregate features')
            delete_features_cascade(self.experiment_id, is_aggregate=True)

            logger.info('compute aggregate features for parent objects')
            statistics = {'Mean', 'Std', 'Sum', 'Min', 'Max'}
            for name, query in mapobject_mappings.iteritems():
                logger.info('create static mapobject type "%s"', name)
                parent_type = session.get_or_create(
                    tm.MapobjectType, name=name, is_static=True
                )
                min_zoom, max_zoom = mapobject_type.calculate_min_max_poly_zoom(
                    maxzoom
                )
                mapobject_type.min_poly_zoom = min_zoom
                mapobject_type.max_poly_zoom = max_zoom
                mapobject_type_id = parent_type.id

                logger.debug('delete existing static mapobjects')
                delete_mapobjects_cascade(self.experiment_id, [parent_type.id])

                with tm.utils.ExperimentConnection(self.experiment_id) as conn:
                    logger.info('create mapobjects of type "%s"', name)
                    for obj in query:
                        # First element: x axis
                        # Second element: inverted y axis
                        ul = (obj.offset[1], -1 * obj.offset[0])
                        ll = (ul[0] + obj.image_size[1], ul[1])
                        ur = (ul[0], ul[1] - obj.image_size[0])
                        lr = (ll[0], ul[1] - obj.image_size[0])
                        # Closed circle with coordinates sorted counter-clockwise
                        contour = np.array([ur, ul, ll, lr, ur])
                        polygon = shapely.geometry.Polygon(contour)

                        mapobject_id = self._add_mapobject(
                            conn, mapobject_type_id
                        )
                        self._add_mapobject_segmentation(
                            conn, mapobject_id, polygon
                        )

                # Moments are computed only over "non-static" mapobjects,
                # i.e. segmented objects within a pipeline
                child_types = session.query(
                        tm.MapobjectType.id, tm.MapobjectType.name
                    ).\
                    filter_by(is_static=False).\
                    all()

                logger.info(
                    'compute features for parent objects of type "%s"',
                    parent_type.name
                )
                # Create the database entries for the new parent features,
                # e.g. mean area of cells per well
                for child_type in child_types:
                    if child_type.name == parent_type.name:
                        continue

                    child_features = session.query(
                            tm.Feature.id, tm.Feature.name
                        ).\
                        filter_by(mapobject_type_id=child_type.id).\
                        all()

                    if not child_features:
                        continue

                    with tm.utils.ExperimentConnection(self.experiment_id) as conn:
                        logger.info(
                            'compute statistics over child objects of '
                            'type "%s"', child_type.name
                        )

                        feature_map = dict()
                        for feature in child_features:
                            for stat in statistics:
                                name = '{name}_{stat}-{type}'.format(
                                    name=feature.name, stat=stat,
                                    type=child_type.name
                                )
                                fid = self._add_feature(
                                    conn, name, parent_type.id, True
                                )
                                feature_map[(stat, feature.id)] = fid
                        name = 'Count-{type}'.format(
                            type=child_type.name
                        )
                        fid = self._add_feature(
                            conn, name, parent_type.id, True
                        )
                        feature_map[('Count', feature.id)] = fid

                        # For each parent mapobject calculate statistics on
                        # features of children, i.e. mapobjects that are covered
                        # by the parent mapobject
                        conn.execute('''
                           SELECT id FROM mapobjects
                           WHERE mapobject_type_id = %(parent_mapobject_type_id)s
                        ''', {
                            'parent_mapobject_type_id': parent_type.id
                        })
                        parent_mapobjects = conn.fetchall()
                        for i, parent in enumerate(parent_mapobjects):
                            logger.debug(
                                'process parent mapobject #%d of type "%s"', i,
                                parent_type.name
                            )
                            data = self._get_aggregate_data(
                                conn, parent.id, child_type.id
                            )
                            if data is None:
                                continue
                            df = pd.DataFrame(
                                data,
                                columns = [
                                    'Mean', 'Std', 'Sum',
                                    'Min', 'Max', 'Count',
                                    'feature_id', 'tpoint'
                                ]
                            )
                            if len(np.unique(df.Count)) > 1:
                                raise ValueError(
                                    'Some feature values were not cleaned up '
                                    'correctly.'
                                )

                            tpoints = np.unique(df.tpoint)
                            for t in tpoints:
                                logger.debug(
                                    'insert values at time point %d', t
                                )
                                vals = dict()
                                for (stat, c_fid), p_fid in feature_map.iteritems():
                                    index = np.logical_and(
                                        df.feature_id == c_fid,
                                        df.tpoint == t
                                    )
                                    if stat == 'Std' and int(df.loc[index, 'Count']) == 1:
                                        vals[p_fid] = 'NaN'
                                    else:
                                        vals[p_fid] = df.loc[index, stat].values[0]
                                self._add_feature_values(
                                    conn, vals, parent.id, t
                                )

                    # TODO: population context as a separate step
                    # tm.types.ST_Expand()

    @staticmethod
    def _add_feature(conn, name, mapobject_type_id, is_aggregate):
        conn.execute('''
            SELECT id FROM features
            WHERE name = %(name)s
            AND mapobject_type_id = %(mapobject_type_id)s;
        ''', {
            'name': name,
            'mapobject_type_id': mapobject_type_id,
            'is_aggregate': is_aggregate
        })
        feature = conn.fetchone()
        if feature is None:
            conn.execute('''
                SELECT * FROM nextval('features_id_seq');
            ''')
            val = conn.fetchone()
            feature_id = val.nextval
            conn.execute('''
                INSERT INTO features (
                    id, name,
                    mapobject_type_id, is_aggregate
                )
                VALUES (
                    %(id)s, %(name)s,
                    %(mapobject_type_id)s, %(is_aggregate)s
                )
                ON CONFLICT
                ON CONSTRAINT features_name_mapobject_type_id_key
                DO NOTHING
            ''', {
                'id': feature_id,
                'name': name,
                'mapobject_type_id': mapobject_type_id,
                'is_aggregate': is_aggregate
            })
        else:
            feature_id = feature.id
        return feature_id

    @staticmethod
    def _add_feature_values(conn, values, mapobject_id, tpoint):
        conn.execute('''
            INSERT INTO feature_values AS v (values, mapobject_id, tpoint)
            VALUES (%(values)s, %(mapobject_id)s, %(tpoint)s)
            ON CONFLICT
            ON CONSTRAINT feature_values_tpoint_mapobject_id_key
            DO UPDATE
            SET values = v.values || %(values)s
            WHERE v.mapobject_id = %(mapobject_id)s
            AND v.tpoint = %(tpoint)s;
        ''', {
            'values': Json(values),
            'mapobject_id': mapobject_id,
            'tpoint': tpoint
        })

    @staticmethod
    def _get_aggregate_data(conn, parent_mapobject_id,
            child_mapobject_type_id):
        conn.execute('''
            SELECT geom_poly FROM mapobject_segmentations
            WHERE mapobject_id = %(mapobject_id)s
            ORDER BY mapobject_id
            LIMIT 1;
        ''', {
            'mapobject_id': parent_mapobject_id
        })
        parent_geom_poly = conn.fetchone()[0]
        # TODO: aggregate JSONB
        conn.execute('''
            SELECT
                avg(value::double precision),
                stddev(value::double precision),
                sum(value::double precision),
                min(value::double precision),
                max(value::double precision),
                count(value::double precision),
                key::integer,
                tmp.tpoint
            FROM (
                SELECT v.tpoint, v.values FROM feature_values v
                JOIN mapobjects m ON m.id = v.mapobject_id
                JOIN mapobject_segmentations s ON s.mapobject_id = m.id
                WHERE v.values is NOT NULL
                AND m.mapobject_type_id = %(mapobject_type_id)s
                AND ST_CoveredBy(s.geom_poly, %(geom_poly)s)
            ) AS tmp, jsonb_each_text(tmp.values)
            GROUP BY (key, tmp.tpoint);
        ''', {
            'mapobject_type_id': child_mapobject_type_id,
            'geom_poly': parent_geom_poly
        })
        return conn.fetchall()

    @staticmethod
    def _add_mapobject(conn, mapobject_type_id):
        conn.execute('''
            SELECT * FROM nextval('mapobjects_id_seq');
        ''')
        val = conn.fetchone()
        mapobject_id = val.nextval

        conn.execute('''
            INSERT INTO mapobjects (id, mapobject_type_id)
            VALUES (%(mapobject_id)s, %(mapobject_type_id)s);
        ''', {
            'mapobject_id': mapobject_id,
            'mapobject_type_id': mapobject_type_id
        })
        return mapobject_id

    @staticmethod
    def _add_mapobject_segmentation(conn, mapobject_id, polygon, t=None, z=None,
            site_id=None, is_border=None, pipeline=None):
        conn.execute('''
            INSERT INTO mapobject_segmentations (
                mapobject_id,
                geom_poly, geom_centroid,
                tpoint, zplane,
                site_id, is_border, pipeline
            )
            VALUES (
                %(mapobject_id)s,
                %(geom_poly)s, %(geom_centroid)s,
                %(tpoint)s, %(zplane)s,
                %(site_id)s, %(is_border)s, %(pipeline)s
            );
        ''', {
            'mapobject_id': mapobject_id,
            'geom_poly': polygon.wkt, 'geom_centroid': polygon.centroid.wkt,
            'tpoint': t, 'zplane': z,
            'site_id': site_id, 'is_border': is_border, 'pipeline': pipeline
        })
