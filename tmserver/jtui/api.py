# TmServer - TissueMAPS server application.
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
"""Jterator user interface view functions."""
import os
import time
import json
import re
import glob
import yaml
import logging
import base64
import subprocess

from natsort import natsorted
from flask import send_file, jsonify, request
from flask_jwt import jwt_required
from flask_jwt import current_identity

import tmlib.models as tm
from tmlib import cfg as libcfg
from tmlib.utils import flatten
from tmlib.workflow import get_step_args
from tmlib.workflow.jobs import RunJob
from tmlib.workflow.jobs import RunJobCollection
import tmlib.workflow.utils as cluster_utils
from tmlib.workflow.jterator.api import ImageAnalysisPipeline
from tmlib.log import configure_logging
from tmlib.workflow.jterator.project import list_projects
from tmlib.workflow.jterator.project import Project
from tmlib.workflow.jterator.project import AvailableModules

from tmserver.extensions import websocket
from tmserver.util import decode_query_ids
from tmserver.util import assert_form_params, assert_query_params
from tmserver.extensions import gc3pie
from tmserver.jtui import jtui
from tmserver.jtui import register_error
from tmserver.error import (
    MalformedRequestError,
    MissingGETParameterError,
    MissingPOSTParameterError,
    ResourceNotFoundError,
    NotAuthorizedError,
    HTTPException
)


logger = logging.getLogger(__name__)


@register_error
class JtUIError(HTTPException):
    '''Error class for Jterator user interface errors that should be reported
    to the client.
    '''

    def __init__(self, message):
        super(JtUIError, self).__init__(message=message, status_code=400)


def _make_thumbnail(figure_file):
    '''Makes a PNG thumbnail of a plotly figure by screen capture.

    Parameters
    ----------
    figure_file: str
        absolute path to the figure file (``".json"`` extension)

    Note
    ----
    Requires the phantomjs library and the "rasterize.js" script.
    The phantomjs executable must be on the `PATH` and the environment
    variable "RASTERIZE" must be set and point to the location of the
    "rasterize.js" file.
    '''
    import plotly
    if not os.path.exists(figure_file):
        logger.warn('figure file does not exist: %s', figure_file)
        html = ''
    else:
        logger.debug('read figure file: %s', figure_file)
        with TextReader(figure_file) as f:
            figure = json.loads(f.read())
        logger.debug('create HTML figure')
        html = plotly.offline.plot(figure, show_link=False, output_type='div')
    html = ''.join([
        '<html>',
        '<head><meta charset="utf-8" /></head>',
        '<body>',
        html,
        '</body>',
        '</html>'
    ])
    # from xhtml2pdf import pisa
    html_file = figure_file.replace('.json', '.html')
    logger.debug('write html file: %s', html_file)
    with TextWriter(html_file) as f:
        # pisa.CreatePDF(html, f)
        f.write(html)
    # Produce thumbnails for html figures by screen capture.
    png_file = figure_file.replace('.json', '.png')
    logger.debug('generate PNG thumbnail file: %s', png_file)
    rasterize_file = os.path.expandvars('$RASTERIZE')
    subprocess.call([
        'phantomjs', rasterize_file, html_file, png_file
    ])
    logger.debug('remove HTML file: %s', html_file)
    os.remove(html_file)


def list_module_names(pipeline):
    '''Lists all names of active module in the pipeline.

    Parameters
    ----------
    pipeline: dict
        pipeline description

    Returns
    -------
    List[str]
        module names
    '''
    modules_names = [
        os.path.splitext(
            os.path.splitext(
                os.path.basename(m['handles'])
            )[0]
        )[0]
        for m in pipeline if m['active']
    ]
    return modules_names


def get_projects(location):
    '''Creates a :class:`Project <tmlib.workflow.jterator.project.Project>`
    object for each Jterator project folder in the `location`.

    Parameters
    ----------
    location: str
        location where to look for Jterator projects

    Returns
    -------
    List[tmlib.workflow.jterator.project.Project]
    '''
    projects = list()

    project_dirs = list_projects(location)
    for proj_dir in project_dirs:
        pipeline = re.search(r'jterator_(.*)', proj_dir).group(1)
        projects.append(Project(proj_dir, pipeline))
    return projects


@jtui.route('/experiments/<experiment_id>/projects')
@jwt_required()
@decode_query_ids()
def get_available_projects(experiment_id):
    '''Lists all Jterator projects available in the data location.
    A project consists of a pipeline description ("pipe") and
    several module descriptions ("handles").
    '''
    logger.info(
        'get available jterator projects for experiment %d', experiment_id
    )
    jt = ImageAnalysisPipeline(
        experiment_id=experiment_id,
        verbosity=logging.INFO,
        pipeline=pipeline
    )
    projects = get_projects(jt.step_location)
    serialized_projects = [yaml.safe_dump(dict(proj)) for proj in projects]
    return jsonify(jtprojects=serialized_projects)


@jtui.route('/experiments/<experiment_id>/projects/<project_name>')
@jwt_required()
@decode_query_ids()
def get_project(experiment_id, project_name):
    '''Returns a single Jterator project for a given experiment.
    A project consists of a pipeline description ("pipe") and
    several module descriptions ("handles"), represented on disk by `.pipe`
    and `.handles` files, respectively.
    '''
    logger.info(
        'get jterator project "%s" for experiment %d',
        project_name, experiment_id
    )
    jt = ImageAnalysisPipeline(
        experiment_id=experiment_id,
        verbosity=logging.INFO,
        pipeline=project_name,
    )
    serialized_project = yaml.safe_dump(jt.project.to_dict())
    return jsonify(jtproject=serialized_project)


@jtui.route('/available_modules')
@jwt_required()
def get_available_modules():
    '''Lists all available Jterator modules in the
    `JtLibrary <https://github.com/TissueMAPS/JtLibrary>`_ repository.
    '''
    logger.info('get list of available jterator modules')
    repo_location = libcfg.modules_home
    modules = AvailableModules(repo_location)
    return jsonify(jtmodules=modules.to_dict())


@jtui.route('/available_pipelines')
@jwt_required()
def get_available_pipelines():
    '''Lists all available Jterator pipelines in the
    `JtLibrary <https://github.com/TissueMAPS/JtLibrary>`_ repository.
    '''
    logger.info('get list of available jterator pipelines')
    pipes_location = os.path.join(libcfg.modules_home, 'pipes')
    pipes = [
        os.path.basename(p)
        for p in list_projects(pipes_location)
    ]
    pipes = []
    return jsonify(jtpipelines=pipes)


@jtui.route('/experiments/<experiment_id>/available_channels')
@jwt_required()
@decode_query_ids()
def get_available_channels(experiment_id):
    '''Lists all channels for a given experiment.'''
    logger.info(
        'get list of available channels for experiment %d', experiment_id
    )
    with tm.utils.ExperimentSession(experiment_id) as session:
        channels = session.query(tm.Channel)
        return jsonify(channels=[c.name for c in channels])


@jtui.route('/module_source_code')
@assert_query_params('module_filename')
@jwt_required()
def get_module_source_code():
    '''Gets the source code for a given module.'''
    module_filename = request.args.get('module_filename')
    logger.info('get source code of module file "%s"', module_filename)
    modules = AvailableModules(libcfg.modules_home)
    files = [
        f for i, f in enumerate(modules.module_files)
        if os.path.basename(f) == module_filename
    ]
    return send_file(files[0])


@jtui.route('/experiments/<experiment_id>/projects/<project_name>/figure')
@jwt_required()
@assert_query_params('module_name', 'job_id')
@decode_query_ids()
def get_module_figure(experiment_id, project_name):
    '''Gets the figure for a given module.'''
    module_name = request.args.get('module_name')
    job_id = request.args.get('job_id', type=int)
    logger.info(
        'get figure for module "%s" and job %d of project "%s" of experiment %d',
        module_name, job_id, project_name, experiment_id
    )
    jt = ImageAnalysisPipeline(
        experiment_id=experiment_id,
        verbosity=logging.INFO,
        pipeline=project_name,
    )
    fig_file = [
        m.build_figure_filename(jt.figures_location, job_id)
        for m in jt.pipeline if m.name == module_name
    ]
    if len(fig_file) == 0:
        return jsonify({
            'success': False,
            'error': 'No figure file found for module "%s"' % module_name
        })
    fig_file = fig_file[0]
    if os.path.exists(fig_file):
        return send_file(fig_file)
    else:
        return jsonify({
            'success': False,
            'error': 'No figure file found for module "%s"' % module_name
        })


@jtui.route(
    '/experiments/<experiment_id>/projects/<project_name>/joblist',
    methods=['POST']
)
@jwt_required()
@decode_query_ids()
def create_joblist(experiment_id, project_name):
    '''Creates a list of jobs for the current project to give the user a
    possiblity to select a site of interest.
    '''
    logger.info(
        'create list of jterator jobs for project "%s" of experiment %d',
        project_name, experiment_id
    )
    metadata = dict()
    with tm.utils.ExperimentSession(experiment_id) as session:
        for index, site in enumerate(session.query(tm.Site)):
            # TODO: Include time point here?
            # Depends on batching in Jterator.
            metadata[index+1] = {
                'plate': site.well.plate.name,
                'well': site.well.name,
                'y': site.y,
                'x': site.x,
            }
    return jsonify({'joblist': metadata})


@jtui.route(
    '/experiments/<experiment_id>/projects/<project_name>/save',
    methods=['POST']
)
@jwt_required()
@assert_form_params('project')
@decode_query_ids()
def save_project(experiment_id, project_name):
    '''Saves modifications of the pipeline and module descriptions to the
    corresponding `.pipe` and `.handles` files.
    '''
    logger.info(
        'save jterator project "%s" of experiment %d',
        project_name, experiment_id
    )
    data = json.loads(request.data)
    project = yaml.load(data['project'])
    jt = ImageAnalysisPipeline(
        experiment_id=experiment_id,
        verbosity=2,
        pipeline=project_name,
        pipe=project['pipe'],
        handles=project['handles'],
    )
    try:
        jt.project.save()
        return jsonify({'success': True})
    except Exception as err:
        raise JtUIError('Project could not be saved:\n%s', str(err))


@jtui.route(
    '/experiments/<experiment_id>/projects/<project_name>/check',
    methods=['POST']
)
@jwt_required()
@assert_form_params('project')
@decode_query_ids()
def check_jtproject(experiment_id, project_name):
    '''Checks pipeline and module descriptions.
    '''
    logger.info(
        'check description of jterator project "%s" of experiment %d',
        project_name, experiment_id
    )
    data = json.loads(request.data)
    project = yaml.load(data['project'])
    jt = ImageAnalysisPipeline(
        experiment_id=experiment_id,
        verbosity=2,
        pipeline=project_name,
        pipe=project['pipe'],
        handles=project['handles'],
    )
    try:
        jt.check_pipeline()
        return jsonify({'success': True})
    except Exception as err:
        raise JtUIError('Pipeline check failed:\n%s' % str(err))



@jtui.route(
    '/experiments/<experiment_id>/projects/<project_name>/delete',
    methods=['POST']
)
@jwt_required()
@decode_query_ids()
def delete_project(experiment_id, project_name):
    '''Removes `.pipe` and `.handles` files from a given Jterator project.
    '''
    logger.info(
        'delete jterator project "%s" of experiment %d',
        project_name, experiment_id
    )
    jt = ImageAnalysisPipeline(
        experiment_id=experiment_id,
        verbosity=2,
        pipeline=project_name
    )
    jt.project.remove()
    return jsonify({'success': True})


@jtui.route(
    '/experiments/<experiment_id>/projects/<project_name>/create',
    methods=['POST']
)
@jwt_required()
@assert_form_params('template')
@decode_query_ids()
def create_jtproject(experiment_id, project_name):
    '''Creates a new jterator project in an existing experiment folder, i.e.
    create a `.pipe` file with an *empty* pipeline description
    and a "handles" subfolder that doesn't yet contain any `.handles` files.

    Return a jtproject object from the newly created `.pipe` file.
    '''
    # experiment_dir = os.path.join(cfg.EXPDATA_DIR_LOCATION, experiment_id)
    data = json.loads(request.data)
    jt = ImageAnalysisPipeline(
        experiment_id=experiment_id,
        verbosity=2,
        pipeline=project_name,
    )
    # TODO
    # Create the project, i.e. create a folder that contains a .pipe file and
    # handles subfolder with .handles files
    if data.get('template', None):
        skel_dir = os.path.join(libcfg.modules_home, 'pipes', data['template'])
    else:
        skel_dir = None
    repo_dir = libcfg.modules_home
    jt.project.create(repo_dir=repo_dir, skel_dir=skel_dir)
    serialized_jtproject = yaml.safe_dump(jt.project.to_dict())
    return jsonify(jtproject=serialized_jtproject)


@jtui.route('/experiments/<experiment_id>/jobs/kill', methods=['POST'])
@assert_form_params('task_id')
@jwt_required()
@decode_query_ids()
def kill_jobs(experiment_id):
    '''Kills submitted jobs.'''
    # TODO
    raise NotImplementedError()


def _get_output(jobs, modules, fig_location):
    output = list()
    if jobs is None:
        return output
    for task in jobs.iter_workflow():
        if not isinstance(task, RunJobCollection):
            continue
        for subtask in task.iter_tasks():
            if not isinstance(subtask, RunJob):
                continue
            j = int(re.search(r'_(\d+)$', subtask.jobname).group(1))
            stdout_file = os.path.join(subtask.output_dir, subtask.stdout)
            if os.path.exists(stdout_file):
                with open(stdout_file) as f:
                    stdout = f.read()
            else:
                stdout = ''
            stderr_file = os.path.join(subtask.output_dir, subtask.stderr)
            if os.path.exists(stderr_file):
                with open(stderr_file) as f:
                    stderr = f.read()
            else:
                stderr = ''

            with tm.utils.MainSession() as session:
                task_info = session.query(tm.Task).get(subtask.persistent_id)
                exitcode = task_info.exitcode
                submission_id = task_info.submission_id
            failed = exitcode != 0
            output.append({
                'id': j,
                'submission_id': submission_id,
                'name': subtask.jobname,
                'stdout': stdout,
                'stderr': stderr,
                'failed': failed
            })
    return output


@jtui.route(
    '/experiments/<experiment_id>/projects/<project_name>/jobs/status',
    methods=['POST']
)
@jwt_required()
@decode_query_ids()
def get_job_status(experiment_id, project_name):
    '''Gets the status of submitted jobs.'''
    jobs = gc3pie.retrieve_jobs(
        experiment_id=experiment_id,
        program='jtui-{project}'.format(project=project_name)
    )
    if jobs is None:
        status_result = {}
    else:
        status_result = gc3pie.get_status_of_submitted_jobs(jobs)
    return jsonify(status=status_result)


@jtui.route(
    '/experiments/<experiment_id>/projects/<project_name>/jobs/output',
    methods=['POST']
)
@jwt_required()
@assert_form_params('project')
@decode_query_ids()
def get_job_output(experiment_id, project_name):
    '''Gets output generated by a previous submission.'''
    data = json.loads(request.data)
    project = yaml.load(data['project'])
    jt = ImageAnalysisPipeline(
        experiment_id=experiment_id,
        verbosity=2,
        pipeline=project_name,
        pipe=project['pipe'],
        handles=project['handles'],
    )
    try:
        jobs = gc3pie.retrieve_jobs(
            experiment_id=experiment_id,
            program='jtui-{pipeline}'.format(pipeline=jt.project.name)
        )
        output = _get_output(jobs, jt.pipeline, jt.figures_location)
        return jsonify(output=output)
    except IndexError:
        return jsonify(output=None)


@jtui.route(
    '/experiments/<experiment_id>/projects/<project_name>/jobs/run',
    methods=['POST']
)
@jwt_required()
@assert_form_params('job_ids', 'project')
@decode_query_ids()
def run_jobs(experiment_id, project_name):
    '''Runs one or more jobs of the current project with pipeline and module
    descriptions provided by the UI.

    This requires the pipeline and module descriptions to be saved to *pipe*
    and *handles* files, respectively.
    '''
    logger.info(
        'submit jobs for jterator pipeline "%s" of experiment %d',
        project_name, experiment_id
    )
    data = json.loads(request.data)
    job_ids = map(int, data['job_ids'])
    project = yaml.load(data['project'])
    jt = ImageAnalysisPipeline(
        experiment_id=experiment_id,
        verbosity=2,
        pipeline=project_name,
        pipe=project['pipe'],
        handles=project['handles']
    )

    # 1. Delete figures and logs from previous submission
    #    since they are not tracked per submission.
    jt.remove_previous_pipeline_output()

    # 2. Build jobs
    batch_args_cls, submit_args_cls, _ = get_step_args('jterator')
    batch_args = batch_args_cls()
    batch_args.batch_size = 1  # only one site per job
    batch_args.plot = True
    # In "run" mode only a few selected jobs will be submitted
    job_descriptions = jt.create_batches(batch_args, job_ids)

    # TODO: remove figure files of previous runs!!
    jt.write_batch_files(job_descriptions)
    with tm.utils.MainSession() as session:
        submission = tm.Submission(
            experiment_id=experiment_id,
            program='jtui-{pipeline}'.format(pipeline=jt.project.name),
            user_id=current_identity.id
        )
        session.add(submission)
        session.flush()

        submit_args = submit_args_cls()
        job_collection = jt.create_run_job_collection(submission.id)
        jobs = jt.create_run_jobs(
            submission_id=submission.id,
            user_name=current_identity.name,
            batches=job_descriptions['run'],
            job_collection=job_collection,
            duration=submit_args.duration,
            memory=submit_args.memory, cores=submit_args.cores
        )

    # 3. Store jobs in session
    gc3pie.store_jobs(jobs)
    # session.remove(data['previousSubmissionId'])
    gc3pie.submit_jobs(jobs)
    return jsonify({'submission_id': jobs.submission_id})
