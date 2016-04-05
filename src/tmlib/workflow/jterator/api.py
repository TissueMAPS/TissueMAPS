import os
import sys
import shutil
import logging
import numpy as np
import matlab_wrapper as matlab
from cached_property import cached_property

import tmlib.models
from tmlib.utils import autocreate_directory_property
from tmlib.utils import notimplemented
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

        with tmlib.models.utils.Session() as session:

            sites = session.query(tmlib.models.Site).\
                join(tmlib.models.Well).\
                join(tmlib.models.Plate).\
                filter(tmlib.models.Plate.experiment_id == self.experiment_id).\
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

                    image_files = session.query(tmlib.models.ChannelImageFile).\
                        join(tmlib.models.Channel).\
                        join(tmlib.models.Site).\
                        filter(tmlib.models.Channel.experiment_id == self.experiment_id).\
                        filter(tmlib.models.Channel.name == ch_name).\
                        filter(tmlib.models.Site.id == site.id).\
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
            # TODO: objects
        return job_descriptions

    def delete_previous_job_output(self):
        '''Deletes all instances of class
        :py:class:`tmlib.models.MapobjectType` as well as all children
        instances for the processed experiment.
        '''
        with tmlib.models.utils.Session() as session:

            mapobject_type = session.query(tmlib.models.MapobjectType).\
                filter(tmlib.models.MapobjectType.experiment_id == self.experiment_id).\
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

    def run_job(self, batch):
        '''Runs the pipeline, i.e. executes modules sequentially.

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

        # Use an in-memory store for pipeline data and only flush/commit them
        # to the database once the whole pipeline completed successfully.
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
        with tmlib.models.utils.Session() as session:
            for channel_name, file_ids in batch['image_file_ids'].iteritems():
                logger.info('load images for channel "%s"', channel_name)
                if channel_info[channel_name]['correct']:
                    logger.info('load illumination statistics')
                    stats_file = session.query(tmlib.models.IllumstatsFile).\
                        join(tmlib.models.Channel).\
                        filter(tmlib.models.Channel.name == channel_name).\
                        filter(tmlib.models.Channel.experiment_id == self.experiment_id).\
                        one()
                    stats = stats_file.get()

                arrays = list()
                for fid in file_ids:
                    image_file = session.query(tmlib.models.ChannelImageFile).\
                        get(fid)
                    logger.info('load image "%s"', image_file.name)
                    image = image_file.get()
                    if channel_info[channel_name]['correct']:
                        logger.info('correct image for illumination artifacts')
                        image = image.correct(stats)
                    logger.info('align image')
                    image = image.align()  # shifted and cropped!
                    arrays.append(image.pixels)

                if len(arrays) > 1:
                    logger.info('stack images along third axis')
                    store['pipe'][channel_name] = np.dstack(arrays)
                else:
                    store['pipe'][channel_name] = arrays[0]

        # Run modules
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

        # Delete all prior mapobjects and feature values for the given site
        # NOTE: this allows use to bulk insert feature values afterwards, since
        # we don't have to worry anymore whether we would create duplicates.
        with tmlib.models.utils.Session() as session:

            mapobjects = session.query(tmlib.models.Mapobject).\
                filter_by(site_id=batch['site_id']).\
                all()
            for m in mapobjects:
                logger.debug('delete map object: %r', m)
                session.delete(m)

        logger.info('write database entries for identified objects')
        with tmlib.models.utils.Session() as session:
            fid = batch['image_file_ids'].values()[0]  # TODO: 3D and time
            image_file = session.query(tmlib.models.ChannelImageFile).get(fid)
            y_offset, x_offset = image_file.site.offset
            # shift = [
            #     s for s in image_file.site.shifts
            #     if s.cycle_id == image_file.cycle_id
            # ][0]
            # y_offset += shift.y
            # x_offset += shift.x
            y_offset += image_file.site.intersection.lower_overhang
            x_offset += image_file.site.intersection.right_overhang
            for obj_name, obj_type in store['segmented_objects'].iteritems():
                logger.info('add mapobject type "%s"', obj_name)
                mapobject_type = session.get_or_create(
                    tmlib.models.MapobjectType,
                    name=obj_name,
                    experiment_id=image_file.site.well.plate.experiment_id
                )
                outlines = obj_type.calc_outlines(y_offset, x_offset)
                feature_ids = dict()
                for f_name in obj_type.measurements:
                    # TODO: This seems to take very long!
                    feature = session.get_or_create(
                        tmlib.models.Feature,
                        name=f_name, mapobject_type_id=mapobject_type.id
                    )
                    feature_ids[f_name] = feature.id
                # NOTE: numpy data types are not supported by SQLalchemy!
                for label in obj_type.labels:
                    logger.debug('add mapobject #%d', label)
                    mapobject = tmlib.models.Mapobject(
                        label=int(label),
                        site_id=image_file.site.id,
                        mapobject_type_id=mapobject_type.id
                    )
                    mapobject.is_border = bool(obj_type.is_border[label])
                    session.add(mapobject)
                    session.flush()
                    # TODO: 3D and time
                    # Create a string representation of the polygon using the
                    # EWKT format, e.g. "POLGON((1 2,3 4,6 7)))"
                    logger.debug('add outline')
                    geom_poly = 'POLYGON((%s))' % ','.join([
                        '%d %d' % (coordinate.x, coordinate.y)
                        for i, coordinate in outlines[label].iterrows()
                    ])
                    centroid = np.mean(outlines[label])
                    geom_centroid = 'POINT(%.2f %.2f)' % (
                        centroid.x, centroid.y
                    )
                    mapobject_outline = tmlib.models.MapobjectOutline(
                        tpoint=image_file.tpoint, zplane=image_file.zplane,
                        mapobject_id=mapobject.id, geom_poly=geom_poly,
                        geom_centroid=geom_centroid
                    )
                    session.add(mapobject_outline)
                    session.flush()
                    logger.debug('add feature values')
                    feature_values = list()
                    for f_name, f_id in feature_ids.iteritems():
                        fvalue = tmlib.models.FeatureValue(
                            tpoint=image_file.tpoint,
                            feature_id=f_id,
                            mapobject_id=mapobject.id,
                            value=float(
                                obj_type.measurements.loc[label, f_name]
                            )
                        )
                        feature_values.append(fvalue)
                    session.add_all(feature_values)
                    session.flush

            # max_z = 6
            # n_points_in_tile_per_z = calculate_n_points_in_tile(
            #     session, max_z,
            #     mapobject_outline_ids=[o.id for o in outline_objects],
            #     n_tiles_to_sample=10)

            # min_poly_zoom = min([z for z, n in n_points_in_tile_per_z.items()
            #                      if n <= N_POINTS_PER_TILE_LIMIT])
            # mapobject_type.min_poly_zoom = min_poly_zoom
            # session.flush()

    @notimplemented
    def collect_job_output(self, batch):
        # TODO: calculate per site, well, and plate statistics
        pass


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
