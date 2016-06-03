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

from tmaps.extensions import websocket
from tmaps.util import extract_model_from_path
from tmaps.extensions import gc3pie
from tmaps.extensions import db

import tmlib.models as tm
from tmlib.models import Experiment
from tmlib.utils import flatten
from tmlib.workflow.registry import get_step_args
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


@jtui.route('/get_available_jtprojects/<path:experiment_id>')
@jwt_required()
@extract_model_from_path(Experiment, check_ownership=True)
def get_available_jtprojects(experiment):
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
        experiment_id=experiment.id,
        verbosity=logging.INFO,
        pipeline=pipeline
    )
    projects = get_projects(jt.step_location)
    serialized_projects = [yaml.safe_dump(dict(proj)) for proj in projects]
    return jsonify(jtprojects=serialized_projects)


@jtui.route('/get_jtproject/<path:experiment_id>/<path:project_name>')
@jwt_required()
@extract_model_from_path(Experiment, check_ownership=True)
def get_jtproject(experiment, project_name):
    '''Returns a single Jterator project for a given experiment.
    A project consists of a pipeline description ("pipe") and
    several module descriptions ("handles"), represented on disk by `.pipe`
    and `.handles` files, respectively.

    Parameters
    ----------
    experiment: tmlib.models.Experiment
        processed experiment
    project_name: str
        name of the pipeline

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
    jt = ImageAnalysisPipeline(
        experiment_id=experiment.id,
        verbosity=logging.INFO,
        pipeline=project_name,
    )
    serialized_project = yaml.safe_dump(jt.project.as_dict())
    return jsonify(jtproject=serialized_project)


@jtui.route('/get_available_jtmodules')
@jwt_required()
def get_available_jtmodules():
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
    repo_location = current_app.config.get('JTLIB_HOME')
    if repo_location is None:
        raise Exception(
            'You have to set the config `JTLIB_HOME` to the '
            ' location of the Jterator modules.'
        )
    modules = AvailableModules(repo_location)
    return jsonify(jtmodules=modules.as_dict())


@jtui.route('/get_available_jtpipelines')
@jwt_required()
def get_available_jtpipelines():
    '''Lists all available Jterator pipelines in the
    `JtLibrary <https://github.com/TissueMAPS/JtLibrary>`_ repository.

    Returns
    -------
    str
        JSON string with "jtpipelines" key. The corresponding value is an
        array of strings.
    '''
    pipes = [
        os.path.basename(p)
        for p in list_projects(os.path.join(current_app.config.get('JTLIB_HOME'), 'pipes'))
    ]
    pipes = []
    return jsonify(jtpipelines=pipes)


@jtui.route('/get_available_channels/<path:experiment_id>')
@jwt_required()
@extract_model_from_path(Experiment, check_ownership=True)
def get_available_channels(experiment):
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
    with tm.utils.Session() as session:
        channels = experiment.channels
        return jsonify(channels=[c.name for c in channels])


@jtui.route('/get_module_source_code/<path:module_filename>')
@jwt_required()
def get_module_source_code(module_filename):
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
    modules = AvailableModules(current_app.config.get('JTLIB_HOME'))
    files = [
        f for i, f in enumerate(modules.module_files)
        if os.path.basename(f) == module_filename
    ]
    return send_file(files[0])


@jtui.route('/get_module_figure/<path:experiment_id>/<path:project_name>/<path:module_name>/<path:job_id>')
@jwt_required()
@extract_model_from_path(Experiment, check_ownership=True)
def get_module_figure(experiment, project_name, module_name, job_id):
    '''Gets the figure for a given module.

    Parameters
    ----------
    experiment: tmlib.models.Experiment
        ID of the processed experiment
    project_name: str
        name of the project (pipeline)
    module_name: str
        name of the module
    job_id: int
        ID of the computational job

    Returns
    -------
    str
        html figure representation
    '''
    jt = ImageAnalysisPipeline(
        experiment_id=experiment.id,
        verbosity=logging.INFO,
        pipeline=project_name,
    )
    fig_file = [
        m.build_figure_filename(jt.figures_location, int(job_id))
        for m in jt.pipeline if m.name == module_name
    ]
    if len(fig_file) == 0:
        return None
    fig_file = fig_file[0]
    if os.path.exists(fig_file):
        return send_file(fig_file)
    else:
        return None


@jtui.route('/create_joblist/<path:experiment_id>', methods=['POST'])
@jwt_required()
@extract_model_from_path(Experiment, check_ownership=True)
def create_joblist(experiment):
    '''Creates a list of jobs for the current project to give the user a
    possiblity to select a site of interest.

    Returns
    -------
    str
        JSON string with "joblist" key
    '''
    data = json.loads(request.data)
    data = yaml.load(data['jtproject'])
    jt = ImageAnalysisPipeline(
        experiment_id=experiment.id,
        verbosity=logging.INFO,
        pipeline=data['name']
    )
    batch_args_cls, submit_args_cls, _ = get_step_args('jterator')
    batch_args = batch_args_cls()
    batches = jt.create_batches(batch_args)
    metadata = list()
    try:
        with tm.utils.Session() as session:
            metadata = dict()
            for batch in batches['run']:
                f = session.query(tm.ChannelImageFile).\
                    filter_by(site_id=batch['site_id']).\
                    first()
                metadata[batch['id']] = {
                    'tpoint': f.tpoint,
                    'zplane': f.zplane,
                    'channel_name': f.channel.name,
                    'well': f.site.well.name,
                    'well_position': [f.site.y, f.site.x],
                    'plate': f.site.well.plate.name
                }
            return jsonify({'joblist': metadata})
    except Exception, e:
        error = str(e)
        print 'Error upon joblist creation: ', error
        return jsonify({'joblist': None, 'error': error})


@jtui.route('/save_jtproject/<path:experiment_id>', methods=['POST'])
@jwt_required()
@extract_model_from_path(Experiment, check_ownership=True)
def save_jtproject(experiment):
    '''Saves modifications of the pipeline and module descriptions to the
    corresponding `.pipe` and `.handles` files.
    '''
    data = json.loads(request.data)
    data = yaml.load(data['jtproject'])
    jt = ImageAnalysisPipeline(
        experiment_id=experiment.id,
        verbosity=1,
        pipeline=data['name'],
        pipe=data['pipe'],
        handles=data['handles'],
    )
    try:
        jt.project.save()
        return jsonify({'success': True})
    except Exception as e:
        error = str(e)
        print 'Error upon saving project: ', error
        return jsonify({'success': False, 'error': error})


@jtui.route('/check_jtproject/<path:experiment_id>', methods=['POST'])
@jwt_required()
@extract_model_from_path(Experiment, check_ownership=True)
def check_jtproject(experiment):
    '''Checks pipeline and module descriptions.
    '''
    data = json.loads(request.data)
    data = yaml.load(data['jtproject'])
    jt = ImageAnalysisPipeline(
        experiment_id=experiment.id,
        verbosity=1,
        pipeline=data['name'],
        pipe=data['pipe'],
        handles=data['handles'],
    )
    try:
        jt.check_pipeline()
        return jsonify({'success': True})
    except Exception as e:
        error = str(e)
        print 'Error upon checking pipeline: ', error
        return jsonify({'success': False, 'error': error})


@jtui.route('/remove_jtproject/<path:experiment_id>', methods=['POST'])
@jwt_required()
@extract_model_from_path(Experiment, check_ownership=True)
def remove_jtproject(experiment):
    '''Removes `.pipe` and `.handles` files from a given Jterator project.

    Returns
    -------
    str
        JSON object with keys "success" and "error"
    '''
    data = json.loads(request.data)
    data = yaml.load(data['jtproject'])
    jt = ImageAnalysisPipeline(
        experiment_id=experiment.id,
        verbosity=1,
        pipeline=data['name'],
        pipe=data['pipe'],
        handles=data['handles'],
    )
    try:
        jt.project.remove()
        return jsonify({'success': True})
    except Exception as e:
        error = str(e)
        print error
        return jsonify({'success': False, 'error': error})


@jtui.route('/create_jtproject/<path:experiment_id>', methods=['POST'])
@jwt_required()
@extract_model_from_path(Experiment, check_ownership=True)
def create_jtproject(experiment):
    '''Creates a new jterator project in an existing experiment folder, i.e.
    create a `.pipe` file with an *empty* pipeline description
    and a "handles" subfolder that doesn't yet contain any `.handles` files.

    Return a jtproject object from the newly created `.pipe` file.

    Returns
    -------
    str
        JSON string with "jtproject" key. The corresponding value is encoded
        in YAML format:

        .. code-block:: yaml

                name: <project_name>
                pipe:
                    name: <pipeline>
                    description:
                        project:
                            lib: ''
                        input:
                            channels: []
                        pipeline: []
                    },
                },
                handles: []
    }
    '''
    # experiment_dir = os.path.join(cfg.EXPDATA_DIR_LOCATION, experiment_id)
    data = json.loads(request.data)
    jt = ImageAnalysisPipeline(
        experiment_id=experiment.id,
        verbosity=1,
        pipeline=data['name'],
        pipe=data['pipe'],
        handles=data['handles'],
    )
    # Create the project, i.e. create a folder that contains a .pipe file and
    # handles subfolder with .handles files
    if data.get('skeleton', None):
        skel_dir = os.path.join(
            current_app.config.get('JTLIB_HOME'), 'pipes', data['skeleton']
        )
    else:
        skel_dir = None
    jt.project.create(repo_dir=current_app.config.get('JTLIB_HOME'), skel_dir=skel_dir)
    serialized_jtproject = yaml.safe_dump(jt.project.as_dict())
    return jsonify(jtproject=serialized_jtproject)


@jtui.route('/kill_jobs', methods=['POST'])
@jwt_required()
def kill_jobs():
    '''Kills submitted jobs.

    Returns
    -------
    str
        JSON object with keys "success" and "error"
    '''
    data = json.loads(request.data)
    persistent_id = data['taskId']
    # TODO
    if persistent_id:
        try:
            task = tasks[persistent_id]
            logger.info('kill job: ', persistent_id)
            engine.kill(task)
            return jsonify({'success': True})
        except Exception as e:
            error = str(e)
            print 'Error upon killing job %d: ' % persistent_id
            print error
            return jsonify({'success': False, 'error': error})
    else:
        return jsonify({'success': False, 'error': 'No jobs were specified.'})


def _get_output(jobs, modules, log_location, fig_location):
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
            if not stdout and not stderr:
                log = '-- Job is still running --'
            else:
                log = stdout + '\n' + stderr
            module_output = list()
            for m in modules:
                stdout_file, stderr_file = m.build_log_filenames(log_location, j)
                fig_file = m.build_figure_filename(fig_location, j)
                thumbnail_file = fig_file.replace('.json', '.png')
                out = dict()
                out['name'] = m.name
                if os.path.exists(stdout_file):
                    with open(stdout_file, 'r') as f:
                        out['stdout'] = f.read()
                    with open(stderr_file, 'r') as f:
                        out['stderr'] = f.read()
                else:
                    out['stdout'] = None
                    out['stderr'] = None
                if os.path.exists(thumbnail_file):
                    with open(thumbnail_file, 'r') as f:
                        out['thumbnail'] = base64.b64encode(f.read())
                else:
                    out['thumbnail'] = None
                module_output.append(out)

            with tm.utils.Session() as session:
                task_info = session.query(tm.Task).get(subtask.persistent_id)
                exitcode = task_info.exitcode
                submission_id = task_info.submission_id
            failed = exitcode != 0
            output.append({
                'id': j,
                'submission_id': submission_id,
                'name': subtask.jobname,
                'log': log,
                'modules': module_output,
                'failed': failed
            })
    return output


@jtui.route('/get_job_status/<path:experiment_id>', methods=['POST'])
@jwt_required()
@extract_model_from_path(Experiment, check_ownership=True)
def get_job_status(experiment):
    '''Gets the status of submitted jobs.

    Parameters
    ----------
    experiment: tmlib.models.Experiment
        processed experiment
    '''
    data = json.loads(request.data)
    data = yaml.load(data['jtproject'])
    jt = ImageAnalysisPipeline(
        experiment_id=experiment.id,
        verbosity=1,
        pipeline=data['name'],
        pipe=data['pipe'],
        handles=data['handles'],
    )
    jobs = gc3pie.retrieve_jobs(
        experiment=experiment,
        submitting_program='jtui-{project}'.format(project=jt.pipe_name)
    )
    if jobs is None:
        status_result = {}
    else:
        status_result = gc3pie.get_status_of_submitted_jobs(jobs)
    return jsonify(status=status_result)


@jtui.route('/get_job_output/<path:experiment_id>', methods=['POST'])
@jwt_required()
@extract_model_from_path(Experiment, check_ownership=True)
def get_job_output(experiment):
    '''Gets output generated by a previous submission.

    Parameters
    ----------
    experiment: tmlib.models.Experiment
        processed experiment

    Returns
    -------
    str
        JSON string with "output" key. The corresponding value has the
        following format:

        .. code-block:: json

            {
                "id": "",
                "submissionId": "",
                "name": "",
                "log": "",
                "time": "",
                "modules": []
            }
    '''
    data = json.loads(request.data)
    data = yaml.load(data['jtproject'])
    jt = ImageAnalysisPipeline(
        experiment_id=experiment.id,
        verbosity=1,
        pipeline=data['name'],
        pipe=data['pipe'],
        handles=data['handles'],
    )
    try:
        jobs = gc3pie.retrieve_jobs(
            experiment=experiment,
            submitting_program='jtui-{project}'.format(project=jt.pipe_name)
        )
        output = _get_output(
            jobs, jt.pipeline, jt.module_log_location, jt.figures_location
        )
        return jsonify(output=output)
    except IndexError:
        return jsonify(output=None)
    except Exception as e:
        error = str(e)
        print 'Error upon output retrieval:', error
        return jsonify(output=None, error=error)


@jtui.route('/run_jobs/<path:experiment_id>', methods=['POST'])
@jwt_required()
@extract_model_from_path(Experiment, check_ownership=True)
def run_jobs(experiment):
    '''Runs one or more jobs of the current project with pipeline and module
    descriptions provided by the UI.

    This requires the pipeline and module descriptions to be saved to *pipe*
    and *handles* files, respectively.
    Parameters

    ----------
    experiment: tmlib.models.Experiment
        processed experiment

    Returns
    -------
    int
        submission ID
    '''
    data = json.loads(request.data)
    job_ids = map(int, data['jobIds'])
    data = yaml.load(data['jtproject'])
    # TODO: sometimes the check fails, although the description seems fine,
    # could it be related to the "hashkey" stuff that javascript adds to the
    # JSON object?
    jt = ImageAnalysisPipeline(
        experiment_id=experiment.id,
        verbosity=1,
        pipeline=data['name'],
        pipe=data['pipe'],
        handles=data['handles'],
    )
    # Remove figure and module log files of previous run
    # to prevent accumulation of data
    # jt.delete_previous_job_output()

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

    jt.write_batch_files(job_descriptions)
    submission = tm.Submission(
        experiment_id=experiment.id,
        program='jtui-{project}'.format(project=jt.pipe_name)
    )
    db.session.add(submission)
    db.session.commit()

    submit_args = submit_args_cls()
    jobs = jt.create_run_jobs(
        submission_id=submission.id,
        user_name=submission.experiment.user.name,
        batches=job_descriptions['run'],
        duration=submit_args.duration,
        memory=submit_args.memory, cores=submit_args.cores
    )

    # 3. Store jobs in session
    gc3pie.store_jobs(experiment, jobs)
    # session.remove(data['previousSubmissionId'])
    logger.info('submit jobs')
    gc3pie.submit_jobs(jobs)
    return jsonify({'submission_id': jobs.submission_id})
