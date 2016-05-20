import os
import sys
import shutil
import logging
import numpy as np
import pandas as pd
import collections
import geoalchemy2.shape
import matlab_wrapper as matlab
from cached_property import cached_property
from sqlalchemy.orm.exc import NoResultFound

import tmlib.models as tm
from tmlib.utils import autocreate_directory_property
from tmlib.utils import flatten
from tmlib.writers import TextWriter
from tmlib.workflow.api import ClusterRoutines
from tmlib.errors import PipelineDescriptionError
from tmlib.logging_utils import map_logging_verbosity
from tmlib.workflow.jterator.utils import complete_path
from tmlib.workflow.jterator.utils import get_module_path
from tmlib.workflow.jterator.project import Project
from tmlib.workflow.jterator.module import ImageAnalysisModule
from tmlib.workflow.jterator.handles import SegmentedObjects
from tmlib.workflow.jterator.checkers import PipelineChecker
from tmlib.workflow.registry import api

logger = logging.getLogger(__name__)


@api('jterator')
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
        self.project = Project(
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
        '''tmlib.jterator.project.Project: jterator project
        '''
        return self._project

    @project.setter
    def project(self, value):
        if not isinstance(value, Project):
            raise TypeError(
                'Attribute "project" must have type '
                'tmlib.jterator.project.Project'
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
        self.check_pipeline()
        job_descriptions = dict()
        job_descriptions['run'] = list()

        channel_names = [
            ch['name']
            for ch in self.project.pipe['description']['input']['channels']
        ]

        with tm.utils.Session() as session:

            sites = session.query(tm.Site).\
                join(tm.Well, tm.Plate).\
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
                        join(tm.Channel, tm.Site).\
                        filter(
                            tm.Channel.experiment_id == self.experiment_id,
                            tm.Channel.name == ch_name,
                            tm.Site.id == site.id
                        ).\
                        all()

                    image_file_paths[ch_name] = [
                        f.location for f in image_files
                    ]
                    # image_file_ids[ch_name] = [
                    #     f.id for f in image_files
                    # ]

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
                    # 'image_file_ids': image_file_ids,
                    'site_id': site.id,
                    'plot': args.plot
                })
        job_descriptions['collect'] = {'inputs': dict(), 'outputs': dict()}
            # TODO: objects
        return job_descriptions

    def delete_previous_job_output(self):
        '''Deletes all instances of class
        :py:class:`tm.MapobjectType` that were generated by a prior run of the
        same pipeline as well as all children instances for the processed
        experiment.
        '''
        # NOTE: This should only be done for the first pipeline, the subsequent
        # pipelines shouldn't remove mapobjects generated by previous ones
        logger.info('delete existing mapobject types')
        with tm.utils.Session() as session:

            mapobject_type_ids = session.query(tm.MapobjectType.id).\
                join(tm.Mapobject).\
                join(tm.MapobjectOutline).\
                join(tm.MapobjectSegmentation).\
                filter(
                    tm.MapobjectType.experiment_id == self.experiment_id,
                    tm.MapobjectSegmentation.pipeline == self.pipe_name,
                    ~tm.MapobjectType.is_static
                ).\
                all()

            if mapobject_type_ids:
                logger.debug('delete existing mapobject types')
                session.query(tm.MapobjectType).\
                    filter(tm.MapobjectType.id.in_(mapobject_type_ids)).\
                    delete()

    def _build_run_command(self, batch):
        # Overwrite method to include "--pipeline" argument
        command = [self.step_name]
        command.extend(['-v' for x in xrange(self.verbosity)])
        command.extend(['--pipeline', self.pipe_name])
        command.append(self.experiment_id)
        command.extend(['run', '--job', str(batch['id'])])
        return command

    def _build_collect_command(self):
        # Overwrite method to include "--pipeline" argument
        command = [self.step_name]
        command.extend(['-v' for x in xrange(self.verbosity)])
        command.extend(['--pipeline', self.pipe_name])
        command.append(self.experiment_id)
        command.append('collect')
        return command

    def run_job(self, batch):
        '''Runs the pipeline, i.e. executes modules sequentially. Once the
        pipeline has run through, outlines and extracted features of segmented
        objects are written into the database.

        Parameters
        ----------
        batch: dict
            job description
        '''
        # TODO: break down into functions

        # Handle pipeline input
        # ---------------------

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

        # Load the images, correct them if requested and align them if required.
        # NOTE: When the experiment was acquired in "multiplexing" mode,
        # images will be automatically aligned, assuming that this is the
        # desired behavior.
        channel_input = self.project.pipe['description']['input']['channels']
        channel_names = [ch['name'] for ch in channel_input]
        mapobject_type_info = self.project.pipe['description']['input'].get(
            'mapobject_types', list()
        )
        mapobject_type_names = [mt['name'] for mt in mapobject_type_info]
        with tm.utils.Session() as session:
            image_metadata = pd.DataFrame(
                session.query(
                    tm.ChannelImageFile.tpoint, tm.ChannelImageFile.zplane
                ).
                join(tm.Channel).
                filter(tm.Channel.experiment_id == self.experiment_id).
                distinct(
                    tm.ChannelImageFile.tpoint, tm.ChannelImageFile.zplane
                ).
                all()
            )
            for channel_name in channel_names:
                logger.info('load images for channel "%s"', channel_name)
                index = channel_names.index(channel_name)
                if channel_input[index]['correct']:
                    logger.info('load illumination statistics')
                    stats_file = session.query(tm.IllumstatsFile).\
                        join(tm.Channel).\
                        filter(
                            tm.Channel.name == channel_name,
                            tm.Channel.experiment_id == self.experiment_id
                        ).\
                        one()
                    stats = stats_file.get()

                image_files = session.query(tm.ChannelImageFile).\
                    join(tm.Channel).\
                    filter(
                        tm.Channel.experiment_id == self.experiment_id,
                        tm.Channel.name == channel_name,
                        tm.ChannelImageFile.site_id == batch['site_id']
                    ).\
                    all()
                images = collections.defaultdict(list)
                for f in image_files:
                    logger.info('load image "%s"', f.name)
                    img = f.get()
                    if channel_input[index]['correct']:
                        logger.info('correct image "%s"', f.name)
                        img = img.correct(stats)
                    logger.debug('align image "%s"', f.name)
                    img = img.align()  # shifted and cropped!
                    images[f.tpoint].append(img.pixels)

                zstacks = list()
                for zplanes in images.itervalues():
                    zstacks.append(np.dstack(zplanes))
                store['pipe'][channel_name] = np.stack(zstacks, axis=-1)

            # Load outlins of mapobjects of the specified types and reconstruct
            # the label images required by modules.
            for mapobject_type_name in mapobject_type_names:
                mapobject_metadata = pd.DataFrame(
                    session.query(
                        tm.MapobjectSegmentation.label,
                        tm.MapobjectOutline.tpoint,
                        tm.MapobjectOutline.zplane,
                        tm.MapobjectOutline.geom_poly
                    ).
                    select_from(tm.MapobjectOutline).
                    join(tm.Mapobject).
                    join(tm.MapobjectType).
                    join(tm.MapobjectSegmentation).
                    filter(
                        tm.MapobjectType.name == mapobject_type_name,
                        tm.MapobjectSegmentation.site_id == batch['site_id'],
                        tm.MapobjectType.experiment_id == self.experiment_id
                    ).
                    all()
                )
                dims = store['pipe'].values()[0].shape
                labeled_pixels = np.zeros(dims, dtype=np.int32)
                y_offset = image_files[0].site.intersection.lower_overhang
                x_offset = image_files[0].site.intersection.right_overhang
                outlines = dict()
                for i, (label, t, z, polygon) in mapobject_metadata.iterrows():
                    poly = geoalchemy2.shape.to_shape(polygon)
                    outlines[(t, z, label)] = poly
                # Add the labeled image to the pipeline and create a handle
                # object to later add measurements for the objects.
                handle = SegmentedObjects(
                    name=mapobject_type_name, key=mapobject_type_name
                )
                handle.from_polygons(outlines, dims, y_offset, x_offset)
                store['pipe'][handle.key] = handle.value
                store['segmented_objects'][handle.key] = handle

        # Remove single-dimensions from image arrays to make it easier to work
        # with.
        # NOTE: It would be more consistent to preserve shape, but most people
        # will work with 2D images and having to deal with additional dimensions
        # would be rather annoying I assume.
        for name, img in store['pipe'].iteritems():
            store['pipe'][name] = np.squeeze(img)

        # Run pipeline
        # ------------

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

        # Write output
        # ------------

        logger.info('write database entries for identified objects')
        with tm.utils.Session() as session:
            mapobject_ids = dict()
            for obj_name, segm_objs in store['segmented_objects'].iteritems():

                logger.debug('add mapobject type "%s"', obj_name)
                mapobject_type = session.get_or_create(
                    tm.MapobjectType,
                    name=obj_name, experiment_id=self.experiment_id,
                )
                logger.info(
                    'add mapobjects of type "%s"', mapobject_type.name
                )

                # Delete existing mapobjects for this site when they were
                # generated in a previous run of the same pipeline. In case
                # they were passed to the pipeline as inputs don't delete them
                # because this means they were generated by another pipeline.
                inputs = self.project.pipe['description']['input'].get(
                    'mapobject_types', list()
                )
                if mapobject_type.name not in inputs:
                    mapobjects = session.query(tm.Mapobject).\
                        join(
                            tm.MapobjectOutline,
                            tm.MapobjectSegmentation
                        ).\
                        filter(
                            tm.Mapobject.mapobject_type_id == mapobject_type.id,
                            tm.MapobjectSegmentation.site_id == batch['site_id'],
                            tm.MapobjectSegmentation.pipeline == self.pipe_name
                        ).\
                        all()
                    logger.debug(
                        'delete existing mapobjects of type "%s"',
                        mapobject_type.name
                    )
                    # NOTE: We delete objects individually rather than on-bulk
                    # to ensure that the session is in sync.
                    for m in mapobjects:
                        session.delete(m)

                # Get existing mapobjects for this site in case they were
                # created by a previous pipeline or create new mapobjects in
                # case they didn't exist (or got just deleted).
                mapobject_ids[mapobject_type.name] = dict()
                for label in segm_objs.labels:
                    logger.debug('add mapobject #%d', label)
                    try:
                        mapobject = session.query(tm.Mapobject).\
                            join(
                                tm.MapobjectOutline,
                                tm.MapobjectSegmentation
                            ).\
                            filter(
                                tm.Mapobject.mapobject_type_id == mapobject_type.id,
                                tm.MapobjectSegmentation.site_id == batch['site_id'],
                                tm.MapobjectSegmentation.label == label,
                                tm.MapobjectSegmentation.pipeline == self.pipe_name
                            ).\
                            one()
                    except NoResultFound:
                        mapobject = tm.Mapobject(mapobject_type.id)
                        session.add(mapobject)
                        session.flush()
                    except:
                        raise
                    mapobject_ids[mapobject_type.name][label] = mapobject.id

        # Write the segmentations, i.e. create a polygon for each segmented
        # object based on the cooridinates of their contours.
        with tm.utils.Session() as session:
            site = session.query(tm.Site).get(batch['site_id'])
            y_offset, x_offset = site.offset
            if site.intersection is not None:
                y_offset += site.intersection.lower_overhang
                x_offset += site.intersection.right_overhang

            for obj_name, segm_objs in store['segmented_objects'].iteritems():
                mapobject_type = session.query(tm.MapobjectType).\
                    filter_by(name=obj_name, experiment_id=self.experiment_id).\
                    one()
                logger.info(
                    'add outlines for mapobjects of type "%s"',
                    mapobject_type.name
                )
                polygons = segm_objs.to_polygons(y_offset, x_offset)
                for (t, z, label), poly in polygons.iteritems():
                    mapobject = session.query(tm.Mapobject).\
                        get(mapobject_ids[mapobject_type.name][label])
                    logger.debug('add outlines for mapobject #%d', label)
                    mapobject_outline = session.get_or_create(
                        tm.MapobjectOutline,
                        tpoint=t, zplane=z,
                        mapobject_id=mapobject.id,
                        geom_poly=poly.wkt,
                        geom_centroid=poly.centroid.wkt
                    )
                    session.add(mapobject_outline)
                    session.flush()

                    mapobject_segm = tm.MapobjectSegmentation(
                        pipeline=self.pipe_name, label=label,
                        site_id=batch['site_id'],
                        mapobject_outline_id=mapobject_outline.id
                    )
                    mapobject_segm.is_border = bool(
                        segm_objs.is_border[t][label]
                    )
                    session.add(mapobject_segm)

        # Create entries for features
        with tm.utils.Session() as session:
            for obj_name, segm_objs in store['segmented_objects'].iteritems():
                mapobject_type = session.query(tm.MapobjectType).\
                    filter_by(name=obj_name, experiment_id=self.experiment_id).\
                    one()
                logger.info(
                    'add features for mapobject of type "%s"',
                    mapobject_type.name
                )
                # TODO: get_or_create_all() may fail???
                # features = session.get_or_create_all(
                #     tm.Feature,
                #     [{'name': fname, 'mapobject_type_id': mapobject_type.id}
                #      for fname in segm_objs.measurements]
                # )
                features = list()
                for fname in segm_objs.measurements[0].columns:
                    features.append(
                        session.get_or_create(
                            tm.Feature,
                            name=fname, mapobject_type_id=mapobject_type.id
                        )
                    )

                logger.debug(
                    'delete existing feature values for mapobject type "%s"',
                    mapobject_type.name
                )
                current_feature_ids = [f.id for f in features]
                current_mapobject_ids = mapobject_ids[mapobject_type.name].values()
                feature_values = session.query(tm.FeatureValue).\
                    filter(
                        tm.FeatureValue.feature_id.in_(current_feature_ids),
                        tm.FeatureValue.mapobject_id.in_(current_mapobject_ids)
                    ).\
                    delete()

        # Create an entry for each measured featured value.
        # This is quite a heavy write operation, since we have nxp feature
        # values, where n is the number of mapobjects and p the number of
        # extracted features.
        with tm.utils.Session() as session:
            feature_values = list()
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
                    logger.debug('add feature values for mapobject #%d', label)
                    mapobject = session.query(tm.Mapobject).\
                        get(mapobject_ids[mapobject_type.name][label])
                    for f in features:
                        logger.debug('add value for feature "%s"' % f.name)
                        for t, measurement in enumerate(segm_objs.measurements):
                            fvalue = measurement.loc[label, f.name]
                            feature_values.append(
                                tm.FeatureValue(
                                    tpoint=t, feature_id=f.id,
                                    mapobject_id=mapobject.id,
                                    value=float(fvalue)
                                )
                            )
            logger.info('insert feature values into table')
            session.bulk_save_objects(feature_values)

    def collect_job_output(self, batch):
        '''Performs the following calculations after the pipeline has been
        run for all jobs::
            - Zoom level at which mapobjects should be represented on the map
              by centroid points rather than the outline polygons.
            - Statistics over features of child mapobjects, i.e. mapobjects
              that are contained by a given mapobject of another type, such as
              the average area of cells within a  well.
            - Population context statistics, i.e. the density of mapobjects
              in the neighborhood of a given mapobject of the same type, such
              as the number of cells that touch a given cell.

        Parameters
        ----------
        batch: dict
            job description
        '''
        logger.info('clean-up mapobjects with invalid geometry')
        with tm.utils.Session() as session:
            ids = session.query(tm.Mapobject.id).\
                join(tm.MapobjectOutline).\
                filter(~tm.MapobjectOutline.geom_poly.ST_IsValid()).\
                all()
            if ids:
                session.query(tm.Mapobject).\
                    filter(tm.Mapobject.id.in_(ids)).\
                    delete()

        logger.info(
            'calculate minimal zoom level for representation of '
            'mapobjects as polygons'
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

                min_poly_zoom, max_poly_zoom = \
                    mapobject_type.calculate_min_max_poly_zoom(
                        layer.maxzoom_level_index,
                        mapobject_outline_ids=[o.id for o in mapobject_outlines]
                    )

                logger.info(
                    'zoom level for mapobjects of type "%s": %d',
                    mapobject_type.name, min_poly_zoom
                )
                mapobject_type.min_poly_zoom = min_poly_zoom
                mapobject_type.max_poly_zoom = max_poly_zoom

        # TODO: do this in parallel in a separate workflow step
        logger.info('compute statistics over features of children mapobjects')
        with tm.utils.Session() as session:

            logger.info('delete existing aggregate features')
            session.query(tm.Feature).\
                filter(tm.Feature.is_aggregate).\
                delete()

        with tm.utils.Session() as session:
            # For now, calculate moments only for "static" mapobjects,
            # such as "Wells" or "Sites"
            parent_types = session.query(tm.MapobjectType).\
                filter_by(
                    experiment_id=self.experiment_id, is_static=True
                )

            moments = {
                'Mean': np.nanmean, 'Std': np.nanstd, 'Median': np.nanmedian
            }
            for parent_type in parent_types:

                # Moments are computed only over "non-static" mapobjects,
                # i.e. segmented objects within a pipeline
                child_types = session.query(tm.MapobjectType).\
                    filter_by(
                        experiment_id=self.experiment_id, is_static=False
                    )

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
                        'mapobjects of  type "%s"', child_type.name
                    )

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
                                tm.Mapobject, tm.MapobjectOutline
                            ).
                            filter(
                                tm.Mapobject.mapobject_type_id == child_type.id,
                                tm.MapobjectOutline.geom_poly.ST_CoveredBy(
                                    parent.outlines[0].geom_poly
                                )
                            ).
                            all()
                        )
                        if df.empty:
                            # This means that this parent object doesn't cover
                            # any children objects.
                            # TODO: prevent this loop in the first place
                            continue

                        count = 0
                        for feature in child_type.features:
                            index = df.feature_id == feature.id
                            for statistic, function in moments.iteritems():
                                logger.debug(
                                    'compute value of feature "%s"',
                                    parent_features[count].name
                                )
                                for t in np.unique(df.loc[index, 'tpoint']):
                                    val = function(df.loc[index, 'value'])
                                    new_feature_values.append(
                                        tm.FeatureValue(
                                            feature_id=parent_features[count].id,
                                            mapobject_id=parent.id,
                                            value=val, tpoint=t
                                        )
                                    )
                                count += 1
                        # Also compute the number of children objects
                        for t in np.unique(df.tpoint):
                            index = df.tpoint == t
                            val = len(np.unique(df.loc[index, 'mapobject_id']))
                            new_feature_values.append(
                                tm.FeatureValue(
                                    feature_id=parent_features[count].id,
                                    mapobject_id=parent.id,
                                    value=val, tpoint=t
                                )
                            )
                    session.add_all(new_feature_values)

                    # TODO: delete features that don't have any values
                    # ids = [f.id for f in parent_features]
                    # session.query(tm.Feature).\
                    #     filter(tm.Feature.id.in_(ids)).\
                    #     delete()

                    # TODO: population context
                    # tm.types.ST_Expand()

