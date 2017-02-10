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
from tmlib import cfg

logger = logging.getLogger(__name__)


@register_step_api('jterator')
class ImageAnalysisPipeline(ClusterRoutines):

    '''Class for running image processing pipelines.'''

    def __init__(self, experiment_id, verbosity, pipe=None, handles=None):
        '''
        Parameters
        ----------
        experiment_id: int
            ID of the processed experiment
        verbosity: int
            logging level
        pipe: dict, optional
            description of pipeline, i.e. module order and paths to module
            source code and descriptor files (default: ``None``)
        handles: List[dict], optional
            description of module input/output (default: ``None``)

        Note
        ----
        If `pipe` or `handles` are not provided
        they are obtained from the persisted YAML descriptor files on disk.
        '''
        super(ImageAnalysisPipeline, self).__init__(experiment_id, verbosity)
        self.engines = {'Python': None, 'R': None}
        self.project = Project(
            step_location=self.step_location, pipe=pipe, handles=handles
        )

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
            when environment variable "TMAPS_MODULES_HOME" would be required but
            doesn't exist
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

    def create_batches(self, args):
        '''Creates job descriptions for parallel computing.

        Parameters
        ----------
        args: tmlib.workflow.jterator.args.BatchArguments
            step-specific arguments

        Returns
        -------
        Dict[str, List[dict] or dict]
            job descriptions
        '''
        self.check_pipeline()

        channel_names = [
            ch['name']
            for ch in self.project.pipe['description']['input']['channels']
        ]

        if args.plot and args.batch_size != 1:
            raise JobDescriptionError(
                'Batch size must be 1 when plotting is active.'
            )

        job_descriptions = dict()
        job_descriptions['run'] = list()
        job_descriptions['collect'] = {'inputs': dict(), 'outputs': dict()}
        with tm.utils.ExperimentSession(self.experiment_id) as session:
            sites = session.query(tm.Site.id).order_by(tm.Site.id).all()
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
                job_descriptions['run'].append({
                    'id': j + 1,  # job IDs are one-based!
                    'inputs': {
                        'image_files': [f[0] for f in image_file_locations]
                    },
                    'outputs': {},
                    'site_ids': batch,
                    'plot': args.plot,
                    'debug': False
                })

        return job_descriptions

    def delete_previous_job_output(self):
        '''Deletes all instances of
        :class:`MapobjectType <tmlib.models.mapobject.MapobjectType>`
        that were generated by a prior run of the same pipeline as well as all
        children instances for the processed experiment.
        '''
        logger.info('delete existing mapobjects and mapobject types')
        with tm.utils.ExperimentConnection(self.experiment_id) as connection:
            tm.MapobjectType.delete_cascade(connection, ref_type='NULL')

    def _load_pipeline_inputs_debug(self):
        logger.info('load pipeline inputs from files for debugging')
        # Use an in-memory store for pipeline data and only insert outputs
        # into the database once the whole pipeline has completed successfully.
        store = {
            'pipe': dict(),
            'current_figure': list(),
            'objects': dict(),
            'channels': list()
        }

        channel_input = self.project.pipe['description']['input'].get(
            'channels', list()
        )
        for item in channel_input:
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
                store['pipe'][item['name']] = f.read()

        return store

    def _load_pipeline_inputs(self, site_id):
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
        channel_input = self.project.pipe['description']['input'].get(
            'channels', list()
        )
        with tm.utils.ExperimentSession(self.experiment_id) as session:
            for item in channel_input:
                # NOTE: When "path" key is present, the image is loaded from
                # a file on disk. The image is not further processed, such as
                # corrected for illuminatiion artifacts or aligned.
                images = collections.defaultdict(list)
                site = session.query(tm.Site).get(site_id)
                if item['correct']:
                    logger.info(
                        'load illumination statistics for channel "%s"',
                        item['name']
                    )
                    try:
                        stats_file = session.query(tm.IllumstatsFile).\
                            join(tm.Channel).\
                            filter(tm.Channel.name == item['name']).\
                            one()
                    except NoResultFound:
                        raise PipelineDescriptionError(
                            'No illumination statistics file found for '
                            'channel "%s"' % item['name']
                        )
                    stats = stats_file.get()
                else:
                    stats = None

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
        objects_output = self.project.pipe['description']['output'].get(
            'objects', list()
        )
        for item in objects_output:
            as_polygons = item['as_polygons']
            store['objects'][item['name']].save = True
            store['objects'][item['name']].represent_as_polygons = as_polygons

        with tm.utils.ExperimentSession(self.experiment_id) as session:
            layer = session.query(tm.ChannelLayer).first()
            mapobject_type_ids = dict()
            segmentation_layer_ids = dict()
            objects_to_save = dict()
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
                    name=obj_name
                )
                mapobject_type_ids[obj_name] = mapobject_type.id
                for (t, z), plane in segm_objs.iterplanes():
                    segmentation_layer = session.get_or_create(
                        tm.SegmentationLayer,
                        mapobject_type_id=mapobject_type.id,
                        tpoint=t, zplane=z
                    )
                    segmentation_layer_ids[(obj_name, t, z)] = \
                        segmentation_layer.id
                    # We will update this in collect phase, but we need to set
                    # some limits in case the user already starts viewing
                    # Without any contraints the user interface might explode.
                    poly_thresh = layer.maxzoom_level_index - 3
                    segmentation_layer.polygon_threshold = \
                        0 if poly_thresh < 0 else poly_thresh
                    centroid_thresh = segmentation_layer.polygon_threshold - 2
                    segmentation_layer.centroid_threshold = \
                        0 if centroid_thresh < 0 else centroid_thresh


            site = session.query(tm.Site).get(store['site_id'])
            y_offset, x_offset = site.offset
            if site.intersection is not None:
                y_offset += site.intersection.lower_overhang
                x_offset += site.intersection.right_overhang

        mapobject_ids = dict()
        with tm.utils.ExperimentConnection(self.experiment_id) as conn:
            for obj_name, segm_objs in objects_to_save.iteritems():
                # Delete existing mapobjects for this site when they were
                # generated in a previous run of the same pipeline. In case
                # they were passed to the pipeline as inputs don't delete them
                # because this means they were generated by another pipeline.
                inputs = self.project.pipe['description']['input'].get(
                    'objects', list()
                )
                if obj_name not in inputs:
                    logger.info(
                        'delete segmentations for existing mapobjects of '
                        'type "%s"', obj_name
                    )
                    tm.Mapobject.delete_cascade(
                        conn, mapobject_type_ids[obj_name],
                        ref_type=tm.Site.__name__, ref_id=store['site_id']
                    )

                # Get existing mapobjects for this site in case they were
                # created by a previous pipeline or create new mapobjects in
                # case they didn't exist (or got just deleted).
                logger.info('add objects of type "%s"', obj_name)
                mapobject_ids = dict()
                for label in segm_objs.labels:
                    logger.debug('add object #%d', label)
                    mapobject_ids[label] = tm.Mapobject.add(
                        conn, mapobject_type_ids[obj_name]
                    )

                # Save segmentations, i.e. create a polygon and/or point for
                # each segmented object based on the cooridinates of their
                # contours and centroids, respectively.
                logger.info(
                    'add segmentations for objects of type "%s"', obj_name
                )
                if segm_objs.represent_as_polygons:
                    logger.debug('represent segmented objects as polygons')
                    polygons = segm_objs.to_polygons(y_offset, x_offset)
                    for (t, z, label), polygon in polygons:
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
                        tm.MapobjectSegmentation.add(
                            conn, mapobject_ids[label],
                            segmentation_layer_ids[(obj_name, t, z)],
                            polygon=polygon
                        )
                else:
                    logger.debug('represent segmented objects only as points')
                    centroids = segm_objs.to_points(y_offset, x_offset)
                    for (t, z, label), centroid in centroids:
                        logger.debug(
                            'add segmentation for object #%d at '
                            'tpoint %d and zplane %d', label, t, z
                        )
                        tm.MapobjectSegmentation.add(
                            conn, mapobject_ids[label],
                            segmentation_layer_ids[(obj_name, t, z)],
                            centroid=centroid
                        )

                logger.info('add features for objects of type "%s"', obj_name)
                measurements = segm_objs.measurements
                feature_ids = dict()
                for fname in measurements[0].columns:
                    logger.debug('add feature "%s"', fname)
                    feature_ids[fname] = self._add_feature(
                        conn, fname, mapobject_type_ids[obj_name]
                    )

                for t, data in enumerate(measurements):
                    if data.empty:
                        logger.warn('empty measurement at time point %d', t)
                        continue
                    for label, d in data.rename(columns=feature_ids).iterrows():
                        logger.debug(
                            'add values for mapobject #%d at time point %d',
                            label, t
                        )
                        values = dict(
                            zip(d.index.astype(str), d.values.astype(str))
                        )
                        tm.FeatureValues.add(
                            conn, values, mapobject_ids[label], t
                        )

    def run_job(self, batch):
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
            store = self._load_pipeline_inputs_debug()
            # We use job_id 0 for debugging, which does normally not exist since
            # IDs are one based.
            store = self._run_pipeline(store, 0, True)
        else:
            for site_id in batch['site_ids']:
                logger.info('process site %d', site_id)
                store = self._load_pipeline_inputs(site_id)
                store = self._run_pipeline(store, batch['id'], batch['plot'])
                self._save_pipeline_outputs(store)

    def collect_job_output(self, batch):
        '''Computes the optimal representation of each
        :class:`SegmentationLayer <tmlib.models.layer.SegmentationLayer>` on the
        map for zoomable visualization.

        Parameters
        ----------
        batch: dict
            job description
        '''
        logger.info('clean-up mapobjects with invalid or missing segmentations')
        with tm.utils.ExperimentConnection(self.experiment_id) as connection:
            tm.Mapobject.delete_invalid_cascade(connection)
            tm.Mapobject.delete_missing_cascade(connection)

        with tm.utils.ExperimentSession(self.experiment_id) as session:
            layer = session.query(tm.ChannelLayer).first()
            maxzoom = layer.maxzoom_level_index
            segmentation_layers = session.query(tm.SegmentationLayer).all()
            for segm_layer in segmentation_layers:
                pt, ct = segm_layer.calculate_zoom_thresholds(maxzoom)
                segm_layer.polygon_threshold = pt
                segm_layer.centroid_threshold = ct

                # TODO: population context and aggregate features
                # tm.types.ST_Expand()

    @staticmethod
    def _add_feature(conn, name, mapobject_type_id):
        conn.execute('''
            SELECT id FROM features
            WHERE name = %(name)s
            AND mapobject_type_id = %(mapobject_type_id)s;
        ''', {
            'name': name,
            'mapobject_type_id': mapobject_type_id
        })
        feature = conn.fetchone()
        if feature is None:
            conn.execute('''
                SELECT * FROM nextval('features_id_seq');
            ''')
            record = conn.fetchone()
            feature_id = record.nextval
            conn.execute('''
                INSERT INTO features (id, name, mapobject_type_id)
                VALUES (%(id)s, %(name)s, %(mapobject_type_id)s)
                ON CONFLICT
                ON CONSTRAINT features_name_mapobject_type_id_key
                DO NOTHING
            ''', {
                'id': feature_id,
                'name': name,
                'mapobject_type_id': mapobject_type_id
            })
        else:
            feature_id = feature.id
        return feature_id
