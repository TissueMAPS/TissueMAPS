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
from flask import send_file, jsonify, request, Blueprint, current_app
from flask.ext.jwt import jwt_required
from flask.ext.jwt import current_identity

from tmserver.extensions import websocket
from tmserver.util import decode_query_ids
from tmserver.util import assert_form_params, assert_query_params
from tmserver.extensions import gc3pie

import tmlib.models as tm
from tmlib.utils import flatten
from tmlib.workflow import get_step_args
from tmlib.workflow.jobs import RunJob
from tmlib.workflow.jobs import RunJobCollection
import tmlib.workflow.utils as cluster_utils
from tmlib.workflow.jterator.api import ImageAnalysisPipeline
from tmlib.logging_utils import configure_logging
from tmlib.workflow.jterator.project import list_projects
from tmlib.workflow.jterator.project import Project
from tmlib.workflow.jterator.project import AvailableModules


jtui = Blueprint('jtui', __name__)

logger = logging.getLogger(__name__)

# Create websocket for job status update
# websocket = GeventWebSocket(app)
# websocket.timeout = 3600

# socket = None  # for potential re-connection
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
    '''Creates a `Jtproject` object for each Jterator project folder
    in the data location.

    .. Warning::

        In case the `experiment` contains `subexperiments`, only the
        subexperiment folders will be screened for Jterator projects, but not
        the experiment folder itself.

    Parameters
    ----------
    location: str
        location where to look for Jterator projects

    Returns
    -------
    List[Jtproject]
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

    Parameters
    ----------
    experiment: tmlib.models.Experiment
        processed experiment

    Returns
    -------
    str
        JSON string with "jtprojects" key. The corresponding value is a list
        of Jterator project descriptions in YAML format.
    '''
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

    Parameters
    ----------
    experiment: tmlib.models.Experiment
        processed experiment

    Returns
    -------
    str
        JSON string with "jtproject" key. The corresponding value is encoded
        in YAML format:

        .. code-block:: yaml

            name: string
            pipe:
                name: string
                description:
                    project:
                        name: string
                    jobs:
                        folder: string
                        pattern:
                            - name: string
                              expression: string
                            ...
                    pipeline:
                        - handles: string
                          module: string
                          active: boolean
                        ...
            handles:
                - name: string
                  description:
                    input:
                        - name: string
                          class: string
                          value: string or number or list
                        ...
                    output:
                        - name: string
                          class: string
                          value: string or number or list
                        ...
                    plot: boolean
                ...

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
    serialized_project = yaml.safe_dump(jt.project.as_dict())
    return jsonify(jtproject=serialized_project)


@jtui.route('/available_modules')
@jwt_required()
def get_available_modules():
    '''Lists all available Jterator modules in the
    `JtLibrary <https://github.com/TissueMAPS/JtLibrary>`_ repository.

    Returns
    -------
    str
        JSON string with "jtmodules" key. The corresponding value has the
        following format:

        .. code-block:: json

            {
                modules: [
                    {
                        name: string,
                        description: {
                            input: {
                                ...
                            },
                            output: {
                                ...
                            }
                        }
                    },
                    ...
                ],
                registration: [
                    {
                        name: string,
                        description: {
                            module: string,
                            handles: string,
                            active: boolean
                        }
                    },
                    ...
                ]
            }

    '''
    repo_location = current_app.config.get('TMAPS_MODULES_HOME')
    if repo_location is None:
        raise Exception(
            'You have to set the config `TMAPS_MODULES_HOME` to the '
            ' location of the Jterator modules.'
        )
    modules = AvailableModules(repo_location)
    return jsonify(jtmodules=modules.as_dict())


@jtui.route('/available_pipelines')
@jwt_required()
def get_available_pipelines():
    '''Lists all available Jterator pipelines in the
    `JtLibrary <https://github.com/TissueMAPS/JtLibrary>`_ repository.

    Returns
    -------
    str
        JSON string with "jtpipelines" key. The corresponding value is an
        array of strings.
    '''
    pipes_location = os.path.join(
        current_app.config.get('TMAPS_MODULES_HOME'), 'pipes'
    )
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
    '''Lists all channels for a given experiment.

    Parameters
    ----------
    experiment: tmlib.models.Experiment
        processed experiment

    Returns
    -------
    str
       JSON string with "channels" key. The corresponding value is the list of
       layer names that are available for the given experiment
    '''
    with tm.utils.ExperimentSession(experiment_id) as session:
        channels = session.query(tm.Channel)
        return jsonify(channels=[c.name for c in channels])


@jtui.route('/module_source_code')
@assert_query_params('module_filename')
@jwt_required()
def get_module_source_code():
    '''Gets the source code for a given module.

    Parameters
    ----------
    module_filename: str
        name of the module source code file

    Returns
    -------
    str
       content of the module source code file
    '''
    module_filename = request.args.get('module_filename')
    modules = AvailableModules(current_app.config.get('TMAPS_MODULES_HOME'))
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
    '''Gets the figure for a given module.

    Parameters
    ----------
    experiment: tmlib.models.Experiment
        ID of the processed experiment
    project_name: str
        name of the project (pipeline)

    Returns
    -------
    str
        html figure representation
    '''
    module_name = request.args.get('module_name')
    job_id = request.args.get('job_id', type=int)

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
    jt = ImageAnalysisPipeline(
        experiment_id=experiment_id,
        verbosity=logging.INFO,
        pipeline=project_name
    )
    try:
        batches = jt.get_batches_from_files()
    except IOError:
        # NOTE: This may take quite some time for a large experiment.
        batch_args_cls, submit_args_cls, _ = get_step_args('jterator')
        batch_args = batch_args_cls()
        batches = jt.create_batches(batch_args)
    metadata = list()
    try:
        with tm.utils.ExperimentSession(experiment_id) as session:
            metadata = dict()
            for batch in batches['run']:
                f = session.query(tm.ChannelImageFile).\
                    filter_by(site_id=batch['site_id']).\
                    first()
                # TODO: Include time point here?
                # Depends on batching in Jterator.
                metadata[batch['id']] = {
                    'tpoint': f.tpoint,
                    'channel_name': f.channel.name,
                    'plate': f.site.well.plate.name,
                    'well': f.site.well.name,
                    'y': f.site.y,
                    'x': f.site.x,
                }
            return jsonify({'joblist': metadata})
    except Exception, e:
        error = str(e)
        print 'Error upon joblist creation: ', error
        return jsonify({'joblist': None, 'error': error})


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
    data = json.loads(request.data)
    project = yaml.load(data['project'])
    jt = ImageAnalysisPipeline(
        experiment_id=experiment_id,
        verbosity=1,
        pipeline=project_name,
        pipe=project['pipe'],
        handles=project['handles'],
    )
    try:
        jt.project.save()
        return jsonify({'success': True})
    except Exception as e:
        error = str(e)
        print 'Error upon saving project: ', error
        return jsonify({'success': False, 'error': error})


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
    data = json.loads(request.data)
    project = yaml.load(data['project'])
    jt = ImageAnalysisPipeline(
        experiment_id=experiment_id,
        verbosity=1,
        pipeline=project_name,
        pipe=project['pipe'],
        handles=project['handles'],
    )
    try:
        jt.check_pipeline()
        return jsonify({'success': True})
    except Exception as e:
        error = str(e)
        print 'Error upon checking pipeline: ', error
        return jsonify({'success': False, 'error': error})


@jtui.route(
    '/experiments/<experiment_id>/projects/<project_name>/delete',
    methods=['POST']
)
@jwt_required()
@decode_query_ids()
def delete_project(experiment_id, project_name):
    '''Removes `.pipe` and `.handles` files from a given Jterator project.
    '''
    jt = ImageAnalysisPipeline(
        experiment_id=experiment_id,
        verbosity=1,
        pipeline=project_name
    )
    try:
        jt.project.remove()
        return jsonify({'success': True})
    except Exception as e:
        error = str(e)
        print error
        return jsonify({'success': False, 'error': error})


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
        verbosity=1,
        pipeline=project_name,
    )
    # Create the project, i.e. create a folder that contains a .pipe file and
    # handles subfolder with .handles files
    if data.get('template', None):
        skel_dir = os.path.join(
            current_app.config.get('TMAPS_MODULES_HOME'),
            'pipes', data['template']
        )
    else:
        skel_dir = None
    repo_dir = current_app.config.get('TMAPS_MODULES_HOME')
    jt.project.create(repo_dir=repo_dir, skel_dir=skel_dir)
    serialized_jtproject = yaml.safe_dump(jt.project.as_dict())
    return jsonify(jtproject=serialized_jtproject)


@jtui.route('/experiments/<experiment_id>/jobs/kill', methods=['POST'])
@assert_form_params('task_id')
@jwt_required()
@decode_query_ids()
def kill_jobs(experiment_id):
    '''Kills submitted jobs.
    '''
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
    '''Gets the status of submitted jobs.

    Parameters
    ----------
    experiment: tmlib.models.Experiment
        processed experiment
    '''
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
    '''Gets output generated by a previous submission.

    Parameters
    ----------
    experiment: tmlib.models.Experiment
        processed experiment

    '''
    data = json.loads(request.data)
    project = yaml.load(data['project'])
    jt = ImageAnalysisPipeline(
        experiment_id=experiment_id,
        verbosity=1,
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
    except Exception as e:
        error = str(e)
        print 'Error upon output retrieval:', error
        return jsonify(output=None, error=error)


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

    Parameters
    ----------
    experiment: tmlib.models.Experiment
        processed experiment

    '''
    data = json.loads(request.data)
    job_ids = map(int, data['job_ids'])
    project = yaml.load(data['project'])
    jt = ImageAnalysisPipeline(
        experiment_id=experiment_id,
        verbosity=1,
        pipeline=project_name,
        pipe=project['pipe'],
        handles=project['handles']
    )

    # 1. Delete figures and logs from previous submission
    #    since they are not tracked per submission.
    jt.remove_previous_pipeline_output()

    # 2. Build jobs
    logger.info('build jobs')
    batch_args_cls, submit_args_cls, _ = get_step_args('jterator')
    batch_args = batch_args_cls()
    batch_args.plot = True
    # In "run" mode only a few selected jobs will be submitted
    job_descriptions = jt.create_batches(batch_args, job_ids)

    # TODO: remove figure files of previous runs!!
    jt.write_batch_files(job_descriptions)
    with tm.utils.MainSession() as session:
        submission = tm.Submission(
            experiment_id=experiment_id,
            program='jtui-{pipeline}'.format(pipeline=jt.project.name)
        )
        session.add(submission)
        session.flush()

        submit_args = submit_args_cls()
        jobs = jt.create_run_jobs(
            submission_id=submission.id,
            user_name=current_identity.name,
            batches=job_descriptions['run'],
            duration=submit_args.duration,
            memory=submit_args.memory, cores=submit_args.cores
        )

    # 3. Store jobs in session
    gc3pie.store_jobs(jobs)
    # session.remove(data['previousSubmissionId'])
    logger.info('submit jobs')
    gc3pie.submit_jobs(jobs)
    return jsonify({'submission_id': jobs.submission_id})
