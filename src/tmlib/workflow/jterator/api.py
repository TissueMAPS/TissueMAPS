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

import tmlib.models as tm
from tmlib.utils import autocreate_directory_property
from tmlib.utils import flatten
from tmlib.readers import TextReader
from tmlib.readers import ImageReader
from tmlib.writers import TextWriter
from tmlib.workflow.api import ClusterRoutines
from tmlib.errors import PipelineDescriptionError
from tmlib.errors import JobDescriptionError
from tmlib.logging_utils import map_logging_verbosity
from tmlib.workflow.jterator.utils import complete_path
from tmlib.workflow.jterator.utils import get_module_path
from tmlib.workflow.jterator.project import Project
from tmlib.workflow.jterator.module import ImageAnalysisModule
from tmlib.workflow.jterator.handles import SegmentedObjects
from tmlib.workflow.jterator.checkers import PipelineChecker
from tmlib.workflow import register_api

logger = logging.getLogger(__name__)


@register_api('jterator')
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
        libpath = self.project.pipe['description'].get('lib', None)
        if not libpath:
            if 'TMAPS_MODULES_HOME' in os.environ:
                libpath = os.path.expandvars(
                    os.path.expanduser(os.environ['TMAPS_MODULES_HOME'])
                )
            else:
                raise OSError('TMAPS_MODULES_HOME environment variable not set.')
        libpath = complete_path(libpath, self.step_location)
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

                image_files = session.query(tm.ChannelImageFile).\
                    join(tm.Channel).\
                    join(tm.Site).\
                    filter(tm.Channel.name.in_(channel_names)).\
                    filter(tm.Site.id.in_(batch)).\
                    all()

                job_descriptions['run'].append({
                    'id': job_id,
                    'inputs': {
                        'image_files': [f.location for f in image_files]
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
        '''Deletes all instances of class
        :py:class:`tm.MapobjectType` that were generated by a prior run of the
        same pipeline as well as all children instances for the processed
        experiment.
        '''
        logger.info('delete existing mapobject types')
        with tm.utils.ExperimentSession(self.experiment_id) as session:
            mapobject_type_ids = session.query(tm.MapobjectType.id).\
                join(tm.Mapobject).\
                join(tm.MapobjectSegmentation).\
                filter(
                    tm.MapobjectSegmentation.pipeline == self.project.name,
                    ~tm.MapobjectType.is_static
                ).\
                all()
            if mapobject_type_ids:
                logger.debug('delete existing mapobject types')
                session.query(tm.MapobjectType).\
                    filter(tm.MapobjectType.id.in_(mapobject_type_ids)).\
                    delete()

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
                        logger.info('load image "%s"', f.name)
                        img = f.get()
                        if item['correct']:
                            logger.info('correct image "%s"', f.name)
                            img = img.correct(stats)
                        logger.debug('align image "%s"', f.name)
                        img = img.align()  # shifted and cropped!
                        images[f.tpoint].append(img.array)

                store['pipe'][item['name']] = np.stack(images.values(), axis=-1)

            # Load outlins of mapobjects of the specified types and reconstruct
            # the label images required by modules.
            if not debug:
                for mapobject_type_name in mapobject_type_names:
                    segmentations = session.query(
                            tm.MapobjectSegmentation.tpoint,
                            tm.MapobjectSegmentation.zplane,
                            tm.MapobjectSegmentation.label,
                            tm.MapobjectSegmentation.geom_poly
                        ).\
                        join(tm.Mapobject).\
                        join(tm.MapobjectType).\
                        filter(
                            tm.MapobjectType.name == mapobject_type_name,
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
            ][0]
            if plot and plotting_active:
                # TODO: don't store figures per job_id
                figure_file = module.build_figure_filename(
                    self.figures_location, job_id
                )
                with TextWriter(figure_file) as f:
                    f.write(store['current_figure'])

        return store

    def _save_pipeline_outputs(self, store):
        logger.info('save pipeline outputs')
        with tm.utils.ExperimentSession(self.experiment_id) as session:
            mapobject_ids = dict()
            layer = session.query(tm.ChannelLayer).first()
            for obj_name, segm_objs in store['segmented_objects'].iteritems():

                logger.debug('add mapobject type "%s"', obj_name)
                mapobject_type = session.get_or_create(
                    tm.MapobjectType, name=obj_name
                )
                # We will update this in collect phase, but we need to set some
                # limits in case the user already starts viewing objects on the
                # map. Without any contraints the user interface might explode.
                min_poly_zoom = layer.maxzoom_level_index - 3
                mapobject_type.min_poly_zoom = \
                    0 if min_poly_zoom < 0 else min_poly_zoom
                max_poly_zoom = mapobject_type.min_poly_zoom - 2
                mapobject_type.max_poly_zoom = \
                    0 if max_poly_zoom < 0 else max_poly_zoom

                # Delete existing mapobjects for this site when they were
                # generated in a previous run of the same pipeline. In case
                # they were passed to the pipeline as inputs don't delete them
                # because this means they were generated by another pipeline.
                inputs = self.project.pipe['description']['input'].get(
                    'mapobject_types', list()
                )
                if mapobject_type.name not in inputs:
                    mids = session.query(tm.Mapobject.id).\
                        join(tm.MapobjectSegmentation).\
                        filter(
                            tm.Mapobject.mapobject_type_id == mapobject_type.id,
                            tm.MapobjectSegmentation.site_id == store['site_id'],
                            tm.MapobjectSegmentation.pipeline == self.project.name
                        ).\
                        all()
                    if mids:
                        logger.info(
                            'delete segmentations for existing mapobjects of '
                            'type "%s"', mapobject_type.name
                        )
                        session.query(tm.MapobjectSegmentation).\
                            filter(
                                tm.MapobjectSegmentation.mapobject_id.in_(mids)
                            ).\
                            delete()
                        logger.info(
                            'delete feature values for existing mapobjects of '
                            'type "%s"', mapobject_type.name
                        )
                        session.query(tm.FeatureValue).\
                            filter(tm.FeatureValue.mapobject_id.in_(mids)).\
                            delete()
                        session.query(tm.Mapobject).\
                            filter(tm.Mapobject.id.in_(mids)).\
                            delete()

        with tm.utils.ExperimentSession(self.experiment_id) as session:
            mapobject_ids = dict()
            feature_ids = dict()
            for obj_name, segm_objs in store['segmented_objects'].iteritems():

                logger.debug('add mapobject type "%s"', obj_name)
                mapobject_type = session.query(tm.MapobjectType).\
                    filter_by(name=obj_name).\
                    one()
                # Get existing mapobjects for this site in case they were
                # created by a previous pipeline or create new mapobjects in
                # case they didn't exist (or got just deleted).
                mapobject_ids[obj_name] = dict()
                for label in segm_objs.labels:
                    logger.debug('add mapobject #%d', label)
                    try:
                        mapobject = session.query(tm.Mapobject).\
                            join(tm.MapobjectSegmentation).\
                            filter(
                                tm.Mapobject.mapobject_type_id == mapobject_type.id,
                                tm.MapobjectSegmentation.site_id == store['site_id'],
                                tm.MapobjectSegmentation.label == label,
                                tm.MapobjectSegmentation.pipeline == self.project.name
                            ).\
                            one()
                    except NoResultFound:
                        mapobject = tm.Mapobject(mapobject_type.id)
                        session.add(mapobject)
                        session.commit()
                    except:
                        raise
                    mapobject_ids[obj_name][label] = mapobject.id

                logger.info(
                    'add features for mapobject of type "%s"',
                    mapobject_type.name
                )
                feature_ids[obj_name] = dict()
                for fname in segm_objs.measurements[0].columns:
                    feature = session.get_or_create(
                            tm.Feature,
                            name=fname, mapobject_type_id=mapobject_type.id
                        )
                    feature_ids[obj_name][fname] = feature.id

        # Write the segmentations, i.e. create a polygon for each segmented
        # object based on the cooridinates of their contours.
        with tm.utils.ExperimentSession(self.experiment_id) as session:
            site = session.query(tm.Site).get(store['site_id'])
            y_offset, x_offset = site.offset
            if site.intersection is not None:
                y_offset += site.intersection.lower_overhang
                x_offset += site.intersection.right_overhang

            segmentations = list()
            feature_values = list()
            mapobject_segmentations = list()
            for obj_name, segm_objs in store['segmented_objects'].iteritems():
                logger.info(
                    'add segmentations for mapobjects of type "%s"', obj_name
                )
                polygons = segm_objs.to_polygons(y_offset, x_offset)
                for (t, z, label), outline in polygons.iteritems():
                    if outline.is_empty:
                        logger.warn('object without outline')
                        continue
                    logger.debug('add segmentations for mapobject #%d', label)
                    mapobject_segmentations.append(
                        dict(
                            pipeline=self.project.name,
                            label=label,
                            tpoint=t, zplane=z,
                            geom_poly=outline.wkt,
                            geom_centroid=outline.centroid.wkt,
                            site_id=store['site_id'],
                            mapobject_id=mapobject_ids[obj_name][label],
                            is_border=bool(segm_objs.is_border[t][label]),
                        )
                    )

                # Create an entry for each measured featured value.
                # This is quite a heavy write operation, since we have nxp
                # feature values, where n is the number of mapobjects and
                # p the number of extracted features.
                logger.info(
                    'add feature values for mapobjects of type "%s"', obj_name
                )
                for fname, fid in feature_ids[obj_name].iteritems():
                    logger.debug('add value for feature "%s"' % fname)
                    for t, measurement in enumerate(segm_objs.measurements):
                        if measurement.empty:
                            logger.warn('empty "%s" measurement', fname)
                            continue
                        elif fname not in measurement.columns:
                            continue
                        for label in measurement.index:
                            fvalue = measurement.loc[label, fname]
                            feature_values.append(
                                dict(
                                    tpoint=t, feature_id=fid,
                                    mapobject_id=mapobject_ids[obj_name][label],
                                    value=float(fvalue)
                                )
                            )
            logger.info('insert feature values into table')
            session.bulk_insert_mappings(
                tm.FeatureValue, feature_values
            )
            logger.info('insert segmentations into table')
            session.bulk_insert_mappings(
                tm.MapobjectSegmentation, mapobject_segmentations
            )

    def run_job(self, batch):
        '''Runs the pipeline, i.e. executes modules sequentially. Once the
        pipeline has run through, outlines and extracted features of segmented
        objects are written into the database.

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
        '''Performs the following calculations after the pipeline has been
        run for all jobs::
            - Zoom level at which mapobjects should be represented on the map
              by centroid points rather than the outline polygons.
            - Statistics over features of child mapobjects, i.e. mapobjects
              that are contained by a given mapobject of another type, such as
              the average area of cells within a well.

        Parameters
        ----------
        batch: dict
            job description
        '''
        logger.info('clean-up mapobjects with invalid geometry')
        with tm.utils.ExperimentSession(self.experiment_id) as session:
            ids = session.query(tm.Mapobject.id).\
                join(tm.MapobjectSegmentation).\
                filter(~tm.MapobjectSegmentation.geom_poly.ST_IsValid()).\
                all()
            if ids:
                session.query(tm.Mapobject).\
                    filter(tm.Mapobject.id.in_(ids)).\
                    delete()

        logger.info(
            'calculate minimal/maximal zoom level for representation of '
            'mapobjects as polygons or points'
        )
        with tm.utils.ExperimentSession(self.experiment_id) as session:

            layer = session.query(tm.ChannelLayer).first()
            mapobject_types = session.query(tm.MapobjectType).\
                filter_by(is_static=False)

            for mapobject_type in mapobject_types:
                logger.info('')
                segmentation_ids = session.query(tm.MapobjectSegmentation.id).\
                    join(tm.Mapobject).\
                    filter(tm.Mapobject.mapobject_type_id == mapobject_type.id).\
                    all()

                min_poly_zoom, max_poly_zoom = \
                    mapobject_type.calculate_min_max_poly_zoom(
                        layer.maxzoom_level_index,
                        segmentation_ids=segmentation_ids
                    )

                logger.info(
                    'zoom level for mapobjects of type "%s": %d',
                    mapobject_type.name, min_poly_zoom
                )
                mapobject_type.min_poly_zoom = min_poly_zoom
                mapobject_type.max_poly_zoom = max_poly_zoom

        # TODO: for non-static objects do this in parallel in a separate
        # workflow step
        logger.info('compute statistics over features of children mapobjects')
        logger.info('delete existing aggregate features')
        with tm.utils.ExperimentSession(self.experiment_id) as session:
            session.query(tm.Feature).\
                filter_by(is_aggregate=True).\
                delete()

        with tm.utils.ExperimentSession(self.experiment_id) as session:
            # For now, calculate moments only for "static" mapobjects,
            # such as "Wells" or "Sites"
            parent_types = session.query(tm.MapobjectType).\
                filter_by(is_static=True)

            moments = {
                'Mean': np.nanmean, 'Std': np.nanstd, 'Median': np.nanmedian
            }
            for parent_type in parent_types:

                # Moments are computed only over "non-static" mapobjects,
                # i.e. segmented objects within a pipeline
                child_types = session.query(tm.MapobjectType).\
                    filter_by(is_static=False)

                logger.info(
                    'add features for parent mapobjects of type "%s"',
                    parent_type.name
                )

                # Create the database entries for the new parent features,
                # e.g. mean area of cells per well
                for child_type in child_types:
                    if child_type.name == parent_type.name:
                        continue
                    logger.debug(
                        'add features for child mapobjects of type "%s"',
                        child_type.name
                    )
                    parent_features = list()
                    for feature in child_type.features:
                        for statistic in moments.keys():
                            name = '{name}_{statistic}-{type}'.format(
                                name=feature.name, statistic=statistic,
                                type=child_type.name
                            )
                            parent_features.append(
                                tm.Feature(
                                    name=name,
                                    mapobject_type_id=parent_type.id,
                                    is_aggregate=True
                                )
                            )
                    parent_features.append(
                        tm.Feature(
                            name='Count-{type}'.format(type=child_type.name),
                            mapobject_type_id=parent_type.id,
                            is_aggregate=True
                        )
                    )
                    session.add_all(parent_features)
                    session.flush()

                    logger.debug(
                        'compute statistics on features of child '
                        'mapobjects of type "%s"', child_type.name
                    )

                    tpoints = session.query(tm.FeatureValue.tpoint).\
                        distinct().\
                        all()
                    tpoints = [t[0] for t in tpoints]
                    # For each parent mapobject calculate statistics on
                    # features of children, i.e. mapobjects that are covered
                    # by the parent mapobject
                    new_feature_values = list()
                    for i, parent in enumerate(parent_type.mapobjects):
                        logger.debug(
                            'process parent mapobject #%d of type "%s"', i,
                            parent_type.name
                        )
                        df = pd.DataFrame(
                            session.query(
                                tm.FeatureValue.value,
                                tm.FeatureValue.feature_id,
                                tm.FeatureValue.mapobject_id,
                                tm.FeatureValue.tpoint
                            ).
                            join(
                                tm.Mapobject, tm.MapobjectSegmentation
                            ).
                            filter(
                                tm.Mapobject.mapobject_type_id == child_type.id,
                                tm.MapobjectSegmentation.geom_poly.ST_CoveredBy(
                                    parent.segmentations[0].geom_poly
                                )
                            ).
                            all(),
                            columns = [
                                'value', 'feature_id', 'mapobject_id', 'tpoint'
                            ]
                        )
                        # NOTE: some precautions in case the dataframe is empty
                        if df.empty:
                            df['value'] = df['value'].astype(float)
                            df['feature_id'] = df['feature_id'].astype(int)
                            df['mapobject_id'] = df['mapobject_id'].astype(int)
                            df['tpoint'] = df['tpoint'].astype(int)

                        count = 0
                        for feature in child_type.features:
                            index = df.feature_id == feature.id
                            for statistic, function in moments.iteritems():
                                logger.debug(
                                    'compute value of feature "%s"',
                                    parent_features[count].name
                                )
                                for t in tpoints:
                                    val = function(df.loc[index, 'value'])
                                    new_feature_values.append(
                                        dict(
                                            feature_id=parent_features[count].id,
                                            mapobject_id=parent.id,
                                            value=val, tpoint=t
                                        )
                                    )
                                count += 1
                        # Also compute the number of children objects
                        for t in tpoints:
                            index = df.tpoint == t
                            val = len(np.unique(df.loc[index, 'mapobject_id']))
                            new_feature_values.append(
                                dict(
                                    feature_id=parent_features[count].id,
                                    mapobject_id=parent.id,
                                    value=val, tpoint=t
                                )
                            )
                    session.bulk_insert_mappings(
                        tm.FeatureValue, new_feature_values
                    )

                    # TODO: delete features that don't have any values
                    # ids = [f.id for f in parent_features]
                    # session.query(tm.Feature).\
                    #     filter(tm.Feature.id.in_(ids)).\
                    #     delete()

                    # TODO: population context
                    # tm.types.ST_Expand()

