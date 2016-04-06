import os
import sys
import shutil
import logging
import random
import numpy as np
import matlab_wrapper as matlab
from cached_property import cached_property
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.sql import func

import tmlib.models as tm
from tmlib.utils import autocreate_directory_property
from tmlib.utils import flatten
from tmlib.writers import TextWriter
from tmlib.workflow.api import ClusterRoutines
from tmlib.errors import PipelineDescriptionError
from tmlib.logging_utils import map_logging_verbosity
from tmlib.workflow.jterator.utils import complete_path
from tmlib.workflow.jterator.utils import get_module_path
from tmlib.workflow.jterator.project import JtProject
from tmlib.workflow.jterator.module import ImageAnalysisModule
from tmlib.workflow.jterator.checkers import PipelineChecker

logger = logging.getLogger(__name__)


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
        self.pipe_name = pipeline
        self.engines = {'Python': None, 'R': None}
        self.project = JtProject(
            step_location=self.step_location, pipe_name=self.pipe_name,
            pipe=pipe, handles=handles
        )

    @autocreate_directory_property
    def step_location(self):
        '''str: directory where files for job description, pipeline and module
        description, log output, and figures are stored
        '''
        return os.path.join(
            self.workflow_location, '%s_%s' % (self.step_name, self.pipe_name)
        )

    @property
    def project(self):
        '''tmlib.jterator.project.JtProject: jterator project
        '''
        return self._project

    @project.setter
    def project(self, value):
        if not isinstance(value, JtProject):
            raise TypeError(
                'Attribute "project" must have type '
                'tmlib.jterator.project.JtProject'
            )
        self._project = value

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

    @autocreate_directory_property
    def module_log_location(self):
        '''str: location where module log files (standard output and error)
        are located
        '''
        return os.path.join(self.step_location, 'log_modules')

    def remove_previous_output(self):
        '''Removes all figure and module log files.'''
        shutil.rmtree(self.module_log_location)
        shutil.rmtree(self.figures_dir)

    @cached_property
    def pipeline(self):
        '''List[tmlib.jterator.module.JtModule]: pipeline built in modular form
        based on `pipe` and `handles` descriptions

        Raises
        ------
        tmlib.errors.PipelineDescriptionError
            when information in *pipe* description is missing or incorrect
        OSError
            when environment variable "JTLIB" would be required but doesn't
            exist
        '''
        libpath = self.project.pipe['description'].get('lib', None)
        if not libpath:
            if 'JTLIB' in os.environ:
                libpath = os.environ['JTLIB']
            else:
                raise OSError('JTLIB environment variable not set.')
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
        if not pipeline:
            raise PipelineDescriptionError('No pipeline description available')
        return pipeline

    def start_engines(self, plot):
        '''Starts engines required by non-Python modules in the pipeline.
        This should be done only once, since engines may have long startup
        times, which would otherwise slow down the execution of the pipeline.

        Parameters
        ----------
        plot: bool
            whether plots should be generated; when ``False`` Matlab will be
            started with the ``"-nojvm"`` option, which will disable plotting
            functionality

        Note
        ----
        For Matlab, you need to set the MATLABPATH environment variable
        in order to add module dependencies to the Matlab path.
        '''
        languages = [m.language for m in self.pipeline]
        if 'Matlab' in languages:
            logger.info('start Matlab engine')
            # NOTE: It is absolutely necessary to specify these startup options
            # for use parallel processing on the cluster. Otherwise some jobs
            # hang up and get killed due to timeout.
            startup_options = '-nosplash -singleCompThread'
            if not plot:
                # Option minimizes memory usage and improves initial startup
                # speed, but disables plotting functionality, so we can only
                # use it in headless mode.
                startup_options += ' -nojvm'
            logger.debug('Matlab startup options: %s', startup_options)
            self.engines['Matlab'] = matlab.MatlabSession(
                                        options=startup_options)
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
                self.engines['Matlab'].eval(
                    'addpath(genpath(\'{0}\'));'.format(p)
                )
        # if 'Julia' in languages:
        #     print 'jt - Starting Julia engine'
        #     self.engines['Julia'] = julia.Julia()

    def _configure_loggers(self):
        # TODO: configure loggers for Python, Matlab, and R modules
        jtlogger = logging.getLogger('jtlib')
        level = map_logging_verbosity(self.verbosity)
        jtlogger.setLevel(level)

    def create_batches(self, args, job_ids=None):
        '''Creates job descriptions for parallel computing.

        Parameters
        ----------
        args: tmlib.metaconfig.args.JteratorInitArgs
            step-specific arguments
        job_ids: Set[int], optional
            subset of jobs for which descriptions should be generated
            (default: ``None``)

        Returns
        -------
        Dict[str, List[dict] or dict]
            job descriptions
        '''
        self.check_pipeline()
        job_descriptions = dict()
        job_descriptions['run'] = list()

        channel_names = self.project.pipe['description']['input']['channels'].keys()

        with tm.utils.Session() as session:

            sites = session.query(tm.Site).\
                join(tm.Well).\
                join(tm.Plate).\
                filter(tm.Plate.experiment_id == self.experiment_id).\
                all()

            if job_ids is None:
                job_ids = set(range(1, len(sites)+1))

            for j, site in enumerate(sites):

                job_id = j+1  # job IDs are one-based!

                if job_id not in job_ids:
                    continue

                image_file_paths = dict()
                image_file_ids = dict()
                for ch_name in channel_names:

                    image_files = session.query(tm.ChannelImageFile).\
                        join(tm.Channel).\
                        join(tm.Site).\
                        filter(tm.Channel.experiment_id == self.experiment_id).\
                        filter(tm.Channel.name == ch_name).\
                        filter(tm.Site.id == site.id).\
                        all()

                    image_file_paths[ch_name] = [
                        f.location for f in image_files
                    ]
                    image_file_ids[ch_name] = [
                        f.id for f in image_files
                    ]

                job_descriptions['run'].append({
                    'id': job_id,
                    'inputs': {
                        'image_files': image_file_paths
                    },
                    'outputs': {
                        'figure_files': [
                            module.build_figure_filename(
                                self.figures_location, job_id
                            )
                            for module in self.pipeline
                        ],
                        'log_files': flatten([
                            module.build_log_filenames(
                                self.module_log_location, job_id).values()
                            for module in self.pipeline
                        ])
                    },
                    'image_file_ids': image_file_ids,
                    'site_id': site.id,
                    'plot': args.plot
                })

        job_descriptions['collect'] = {'inputs': dict(), 'outputs': dict()}
            # TODO: objects
        return job_descriptions

    def delete_previous_job_output(self):
        '''Deletes all instances of class
        :py:class:`tm.MapobjectType` as well as all children
        instances for the processed experiment.
        '''
        # NOTE: This should only be done for the first pipeline, the subsequent
        # pipelines shouldn't remove mapobjects generated by previous ones
        with tm.utils.Session() as session:
            mapobject_type = session.query(tm.MapobjectType).\
                filter_by(experiment_id=self.experiment_id, is_static=False).\
                all()
            for m in mapobject_type:
                logger.debug('delete mapobject type: %r', m)
                session.delete(m)

    def _build_run_command(self, batch):
        # Overwrite method to include "--pipeline" argument
        command = [self.step_name]
        command.extend(['-v' for x in xrange(self.verbosity)])
        command.append(self.experiment_id)
        command.extend(['run', '--job', str(batch['id'])])
        command.extend(['--pipeline', self.pipe_name])
        return command

    def _build_collect_command(self):
        # Overwrite method to include "--pipeline" argument
        command = [self.step_name]
        command.extend(['-v' for x in xrange(self.verbosity)])
        command.append(self.experiment_id)
        command.append('collect')
        command.extend(['--pipeline', self.pipe_name])
        return command

    def run_job(self, batch):
        '''Runs the pipeline, i.e. executes modules sequentially, and writes
        outlines and extracted features for segmented objects in the database.

        Parameters
        ----------
        batch: dict
            job description
        '''
        checker = PipelineChecker(
            step_location=self.step_location,
            pipe_description=self.project.pipe['description'],
            handles_descriptions=[
                h['description'] for h in self.project.handles
            ]
        )
        checker.check_all()
        self._configure_loggers()
        self.start_engines(batch['plot'])
        job_id = batch['id']

        # Use an in-memory store for pipeline data and only add outputs
        # to the database once the whole pipeline has completed successfully.
        store = {
            'pipe': dict(),
            'current_figure': list(),
            'segmented_objects': dict(),
            'channels': list()
        }

        # Load the images,correct them if requested and align them if required.
        # NOTE: When the experiment was acquired in "multiplexing" mode,
        # images will be aligned automatically, assuming that this is the
        # desired behavior.
        # TODO: Make the alignment optional and give the user the possibility
        # to decide similar to illumination correction.
        channel_info = self.project.pipe['description']['input']['channels']
        with tm.utils.Session() as session:
            for channel_name, file_ids in batch['image_file_ids'].iteritems():
                logger.info('load images for channel "%s"', channel_name)
                if channel_info[channel_name]['correct']:
                    logger.info('load illumination statistics')
                    stats_file = session.query(tm.IllumstatsFile).\
                        join(tm.Channel).\
                        filter(tm.Channel.name == channel_name).\
                        filter(tm.Channel.experiment_id == self.experiment_id).\
                        one()
                    stats = stats_file.get()

                arrays = list()
                for fid in file_ids:
                    image_file = session.query(tm.ChannelImageFile).\
                        get(fid)
                    logger.info('load image "%s"', image_file.name)
                    image = image_file.get()
                    if channel_info[channel_name]['correct']:
                        logger.info('correct image "%s"', image_file.name)
                        image = image.correct(stats)
                    logger.debug('align image "%s"', image_file.name)
                    image = image.align()  # shifted and cropped!
                    arrays.append(image.pixels)

                if len(arrays) > 1:
                    logger.info('stack images along third axis')
                    store['pipe'][channel_name] = np.dstack(arrays)
                else:
                    store['pipe'][channel_name] = arrays[0]

        # Execute modules
        logger.info('run pipeline')
        for i, module in enumerate(self.pipeline):
            logger.info('run module "%s"', module.name)
            module.update_handles(store, batch['plot'])
            output = module.run(self.engines[module.language])

            log_files = module.build_log_filenames(
                self.module_log_location, job_id
            )
            logger.debug('write standard output and error to log files')
            with TextWriter(log_files['stdout']) as f:
                f.write(output['stdout'])
            with TextWriter(log_files['stderr']) as f:
                f.write(output['stderr'])

            if not output['success']:
                sys.exit(output['error_message'])

            store = module.update_store(store)

            if batch['plot']:
                logger.debug('write figure to file')
                figure_file = module.build_figure_filename(
                    self.figures_location, job_id
                )
                with TextWriter(figure_file) as f:
                    f.write(store['current_figure'])

        # Write the output to the database.
        # NOTE: This may be heavy write operations depending on the number of
        # detected objects and extracted features. Therefore, we add objects
        # and features sequentially to reduce the amount of transactions.
        logger.info('write database entries for identified objects')
        with tm.utils.Session() as session:
            fid = batch['image_file_ids'].values()[0]  # TODO: 3D and time
            image_file = session.query(tm.ChannelImageFile).get(fid)
            site_id = image_file.site_id
            tpoint = image_file.tpoint
            mapobject_ids = dict()
            for obj_name, segm_objs in store['segmented_objects'].iteritems():

                logger.info('add mapobject type "%s"', obj_name)
                mapobject_type = session.get_or_create(
                    tm.MapobjectType,
                    name=obj_name, experiment_id=self.experiment_id,
                )
                logger.info(
                    'add mapobjects of type "%s"', mapobject_type.name
                )
                mapobject_ids[mapobject_type.name] = dict()
                for label in segm_objs.labels:
                    logger.debug('add mapobject #%d', label)
                    try:
                        mapobject = session.query(tm.Mapobject).\
                            join(tm.MapobjectOutline).\
                            join(tm.MapobjectSegmentation).\
                            filter(tm.Mapobject.mapobject_type_id == mapobject_type.id).\
                            filter(tm.MapobjectSegmentation.site_id == site_id).\
                            filter(tm.MapobjectSegmentation.label == label).\
                            one()
                        logger.debug(
                            'delete existing outlines for mapobjects of '
                            'type "%s"', mapobject_type.name
                        )
                        for outline in mapobject.outlines:
                            session.delete(outline)
                    except NoResultFound:
                        mapobject = tm.Mapobject(
                            mapobject_type_id=mapobject_type.id
                        )
                        session.add(mapobject)
                        session.flush()
                    except:
                        raise
                    mapobject_ids[mapobject_type.name][label] = mapobject.id

        with tm.utils.Session() as session:
            fid = batch['image_file_ids'].values()[0]  # TODO: 3D and time
            image_file = session.query(tm.ChannelImageFile).get(fid)
            y_offset, x_offset = image_file.site.offset
            y_offset += image_file.site.intersection.lower_overhang
            x_offset += image_file.site.intersection.right_overhang
            for obj_name, segm_objs in store['segmented_objects'].iteritems():

                mapobject_type = session.query(tm.MapobjectType).\
                    filter_by(name=obj_name, experiment_id=self.experiment_id).\
                    one()

                logger.info(
                    'add outlines for mapobjects of type "%s"',
                    mapobject_type.name
                )
                outlines = segm_objs.calc_outlines(y_offset, x_offset)
                for label in segm_objs.labels:
                    mapobject = session.query(tm.Mapobject).\
                        get(mapobject_ids[mapobject_type.name][label])
                    logger.debug('add outline for mapobject #%d', label)
                    geom_poly = 'POLYGON((%s))' % ','.join([
                        '%d %d' % (coordinate.x, coordinate.y)
                        for i, coordinate in outlines[label].iterrows()
                    ])
                    centroid = np.mean(outlines[label])
                    geom_centroid = 'POINT(%.2f %.2f)' % (
                        centroid.x, centroid.y
                    )
                    mapobject_outline = session.get_or_create(
                        tm.MapobjectOutline,
                        tpoint=image_file.tpoint, zplane=image_file.zplane,
                        mapobject_id=mapobject.id, geom_poly=geom_poly,
                        geom_centroid=geom_centroid
                    )
                    # TODO: 3D and time
                    session.add(mapobject_outline)
                    session.flush()

                    mapobject_segm = tm.MapobjectSegmentation(
                        label=label, site_id=site_id,
                        mapobject_outline_id=mapobject_outline.id
                    )
                    mapobject_segm.is_border = bool(
                        segm_objs.is_border[label]
                    )
                    session.add(mapobject_segm)

        with tm.utils.Session() as session:
            for obj_name, segm_objs in store['segmented_objects'].iteritems():
                mapobject_type = session.query(tm.MapobjectType).\
                    filter_by(name=obj_name, experiment_id=self.experiment_id).\
                    one()
                logger.info(
                    'add features for mapobject of type "%s"',
                    mapobject_type.name
                )
                features = session.get_or_create_all(
                    tm.Feature,
                    [{'name': fname, 'mapobject_type_id': mapobject_type.id}
                     for fname in segm_objs.measurements]
                )
                logger.debug(
                    'delete existing feature values for mapobject type "%s"',
                    mapobject_type.name
                )
                for f in features:
                    for v in f.values:
                        session.delete(v)

        with tm.utils.Session() as session:
            for obj_name, segm_objs in store['segmented_objects'].iteritems():
                mapobject_type = session.query(tm.MapobjectType).\
                    filter_by(name=obj_name, experiment_id=self.experiment_id).\
                    one()
                logger.info(
                    'add feature values for mapobjects of type "%s"',
                    mapobject_type.name
                )
                features = session.query(tm.Feature).\
                    filter_by(mapobject_type_id=mapobject_type.id)
                for label in segm_objs.labels:
                    logger.debug('add features for mapobject #%d', label)
                    mapobject = session.query(tm.Mapobject).\
                        get(mapobject_ids[mapobject_type.name][label])
                    feature_values = list()
                    for f in features:
                        fvalue = tm.FeatureValue(
                            tpoint=tpoint, feature_id=f.id,
                            mapobject_id=mapobject.id,
                            value=float(
                                segm_objs.measurements.loc[label, f.name]
                            )
                        )
                        feature_values.append(fvalue)
                    session.add_all(feature_values)

    def collect_job_output(self, batch):
        '''Calculates the zoom level at which mapobjects should be represented
        on the map by centroid points rather than the entire outline polygons
        and computes for each mapobject type statistics over features of
        children mapobjects, e.g. the mean area of cells per well.

        Parameters
        ----------
        batch: dict
            job description
        '''
        logger.info(
            'calculate optimal zoom level for representing mapobjects by '
            'points rather than polygons'
        )
        with tm.utils.Session() as session:

            layer = session.query(tm.ChannelLayer).\
                join(tm.Channel).\
                filter(tm.Channel.experiment_id == self.experiment_id).\
                first()

            mapobject_types = session.query(tm.MapobjectType).\
                filter_by(experiment_id=self.experiment_id, is_static=False)

            for mapobject_type in mapobject_types:

                mapobject_outlines = session.query(tm.MapobjectOutline).\
                    join(tm.Mapobject).\
                    filter(tm.Mapobject.mapobject_type_id == mapobject_type.id).\
                    all()

                n_points_in_tile_per_z = self._calculate_n_points_in_tile(
                    session, layer.maxzoom_level_index, n_sample=10,
                    mapobject_outline_ids=[o.id for o in mapobject_outlines]
                )

                min_poly_zoom = min([
                    z for z, n in n_points_in_tile_per_z.items() if n <= 1500
                ])

                logger.info(
                    'zoom level for mapobjects of type "%s": %d',
                    mapobject_type.name, min_poly_zoom
                )
                mapobject_type.min_poly_zoom = min_poly_zoom

        logger.info('compute statistics over features of children mapobjects')
        with tm.utils.Session() as session:

            features = session.query(tm.Feature).\
                join(tm.MapobjectType).\
                filter(tm.MapobjectType.experiment_id == self.experiment_id).\
                filter(tm.MapobjectType.static).\
                all()
            logger.debug('delete existing features for static mapobject types')
            for f in features:
                session.delete(f)

        stats_to_compute = {'mean': np.nanmean, 'std': np.nanstd}
        with tm.utils.Session() as session:

            logger.info('add features for mapobjects of type "sites"')
            mapobject_types = session.query(tm.MapobjectType).\
                filter_by(experiment_id=self.experiment_id, is_static=False)

            site_mapobject_type = session.query(tm.MapobjectType).\
                filter_by(experiment_id=self.experiment_id, name='sites').\
                one()

            for mapobject_type in mapobject_types:
                logger.info(
                    'compute statistics on features of mapobjects of '
                    'type "%s"', mapobject_type.name
                )
                new_features = list()
                for feature in mapobject_type.features:
                    for statistic in stats_to_compute.keys():
                        name = '{name}_{statistic}_{type}'.format(
                            name=feature.name, statistic=statistic,
                            type=mapobject_type.name
                        )
                        new_features.append(
                            tm.Feature(
                                name=name,
                                mapobject_type_id=site_mapobject_type.id
                            )
                        )
                session.add_all(new_features)
                session.flush()

                count = 0
                new_feature_values = list()
                for feature in mapobject_type.features:

                    for function in stats_to_compute.values():

                        for site_mapobject in site_mapobject_type.mapobjects:

                            feature_values = session.query(tm.FeatureValue).\
                                join(tm.Feature).\
                                join(tm.MapobjectType).\
                                join(tm.Mapobject).\
                                join(tm.MapobjectOutline).\
                                filter(tm.Feature.id == feature.id).\
                                filter(tm.MapobjectType.id == mapobject_type.id).\
                                filter(tm.FeatureValue.tpoint == 0).\
                                filter(
                                    tm.MapobjectOutline.geom_poly.intersects(
                                        site_mapobject.outlines[0].geom_poly
                                    )
                                ).\
                                all()

                            import ipdb; ipdb.set_trace()

                            # TODO: time points

                            new_value = function(
                                [v.value for v in feature_values]
                            )

                            new_feature_values.append(
                                tm.FeatureValue(
                                    feature_id=new_features[count].id,
                                    mapobject_id=site_mapobject.id,
                                    value=new_value
                                )
                            )
                        count += 1
                session.add_all(new_feature_values)

        with tm.utils.Session() as session:

            logger.info('add features for mapobjects of type "wells"')
            mapobject_types = session.query(tm.MapobjectType).\
                filter_by(experiment_id=self.experiment_id, is_static=False)

            well_mapobject_type = session.query(tm.MapobjectType).\
                filter_by(experiment_id=self.experiment_id, name='wells').\
                one()

            for mapobject_type in mapobject_types:
                logger.info(
                    'compute statistics on features of mapobjects of '
                    'type "%s"', mapobject_type.name
                )
                new_features = list()
                for feature in mapobject_type.features:
                    for statistic in stats_to_compute.keys():
                        name = '{name}_{statistic}_{type}'.format(
                            name=feature.name, statistic=statistic,
                            type=mapobject_type.name
                        )
                        new_features.append(
                            tm.Feature(
                                name=name,
                                mapobject_type_id=well_mapobject_type.id
                            )
                        )
                session.add_all(new_features)
                session.flush()

                count = 0
                new_feature_values = list()
                for feature in mapobject_type.features:

                    for function in stats_to_compute.values():

                        for well_mapobject in well_mapobject_type.mapobjects:

                            feature_values = session.query(tm.FeatureValue).\
                                join(tm.Feature).\
                                join(tm.MapobjectType).\
                                join(tm.Mapobject).\
                                join(tm.MapobjectOutline).\
                                filter(tm.Feature.id == feature.id).\
                                filter(tm.MapobjectType.id == mapobject_type.id).\
                                filter(
                                    tm.MapobjectOutline.geom_poly.intersects(
                                        well_mapobject.outlines[0].geom_poly
                                    )
                                ).\
                                filter(tm.FeatureValue.tpoint == 0).\
                                all()

                            new_value = function(
                                [v.value for v in feature_values]
                            )

                            new_feature_values.append(
                                tm.FeatureValue(
                                    feature_id=new_features[count].id,
                                    mapobject_id=well_mapobject.id,
                                    value=new_value
                                )
                            )
                        count += 1
                session.add_all(new_feature_values)

    @staticmethod
    def _calculate_n_points_in_tile(session, max_z, mapobject_outline_ids, n_sample):

        n_points_in_tile_per_z = {}

        for z in range(max_z, -1, -1):
            tilesize = 256 * 2 ** (6 - z)

            rand_xs = [random.randrange(0, 2**z) for _ in range(n_sample)]
            rand_ys = [random.randrange(0, 2**z) for _ in range(n_sample)]

            n_points_in_tile_samples = []
            for x, y in zip(rand_xs, rand_ys):
                x0 = x * tilesize
                y0 = -y * tilesize

                minx = x0
                maxx = x0 + tilesize
                miny = y0 - tilesize
                maxy = y0

                tile = 'LINESTRING({maxx} {maxy},{minx} {maxy}, {minx} {miny}, {maxx} {miny}, {maxx} {maxy})'.format(
                    minx=minx, maxx=maxx, miny=miny, maxy=maxy
                )

                n_points_in_tile = session.query(
                        func.sum(tm.MapobjectOutline.geom_poly.ST_NPoints())
                    ).\
                    filter(
                        tm.MapobjectOutline.id.in_(mapobject_outline_ids),
                        tm.MapobjectOutline.geom_poly.intersects(tile)
                    ).\
                    scalar()

                if n_points_in_tile is not None:
                    n_points_in_tile_samples.append(n_points_in_tile)

            n_points_in_tile_per_z[z] = (
                float(sum(n_points_in_tile_samples)) /
                len(n_points_in_tile_samples)
            )

        return n_points_in_tile_per_z


def factory(experiment_id, verbosity, pipeline, **kwargs):
    '''Factory function for the instantiation of a `jterator`-specific
    implementation of the :py:class:`tmlib.workflow.api.ClusterRoutines`
    abstract base class.

    Parameters
    ----------
    experiment_id: int
        ID of the processed experiment
    verbosity: int
        logging level
    pipeline: str
        name of the pipeline that should be processed
    **kwargs: dict
        optional and ignored keyword arguments

    Returns
    -------
    tmlib.workflow.metaextract.api.ImageAnalysisPipeline
        API instance
    '''
    pipe = kwargs.get('pipe', None)
    handles = kwargs.get('handles', None)
    return ImageAnalysisPipeline(
        experiment_id, verbosity, pipeline, pipe, handles
    )
