import os
import time
import json
import re
import glob
import yaml
import logging

from natsort import natsorted
from flask import send_file, jsonify, request, Blueprint, current_app
from flask.ext.jwt import jwt_required
import gc3libs

from tmaps.extensions import websocket
import tmlib.models as tm
from tmlib.workflow.registry import get_step_args
import tmlib.workflow.utils as cluster_utils
from tmlib.workflow.jterator.api import ImageAnalysisPipeline
from tmlib.logging_utils import configure_logging
from tmlib.workflow.jterator.project import list_projects
from tmlib.workflow.jterator.project import Project
from tmlib.workflow.jterator.project import AvailableModules


jtui = Blueprint('jtui', __name__)

# configure loggers
configure_logging(logging.INFO)
logger = logging.getLogger(__name__)

tmlib_logger = logging.getLogger('tmlib')
tmlib_logger.setLevel(logging.INFO)
gc3libs_logger = logging.getLogger('gc3.gc3libs')
gc3libs_logger.setLevel(logging.CRITICAL)
apscheduler_logger = logging.getLogger('apscheduler')
apscheduler_logger.setLevel(logging.CRITICAL)


# Create GC3Pie engine for job submission
# e = gc3libs.create_engine()
# e.retrieve_overwrites = True
# engine = BgEngine('gevent', e)
# engine.start(1)

# Create websocket for job status update
# websocket = GeventWebSocket(app)
# websocket.timeout = 3600

# socket = None  # for potential re-connection

# tasks = dict()



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
def get_available_jtprojects(experiment_id):
    '''Lists all Jterator projects available in the data location.
    A project consists of a pipeline description ("pipe") and
    several module descriptions ("handles").

    Parameters
    ----------
    experiment_id: int
        ID of the processed experiment

    Returns
    -------
    str
        JSON string with "jtprojects" key. The corresponding value is a list
        of Jterator project descriptions in YAML format.

    See also
    --------
    `get_jtproject`
    '''
    jt = ImageAnalysisPipeline(
        experiment_id=experiment_id,
        verbosity=logging.INFO,
        pipeline=pipeline
    )
    projects = get_projects(jt.step_location)
    serialized_projects = [yaml.safe_dump(dict(proj)) for proj in projects]
    return jsonify(jtprojects=serialized_projects)

@jtui.route('/get_jtproject/<path:experiment_id>/<path:pipeline>')
# @jwt_required()
def get_jtproject(experiment_id, pipeline):
    '''Returns a single Jterator project for a given experiment.
    A project consists of a pipeline description ("pipe") and
    several module descriptions ("handles"), represented on disk by `.pipe`
    and `.handles` files, respectively.

    Parameters
    ----------
    experiment_id: int
        ID of the processed experiment
    pipeline: str
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
        experiment_id=experiment_id,
        verbosity=logging.INFO,
        pipeline=pipeline,
    )
    serialized_project = yaml.safe_dump(jt.project.as_dict())
    return jsonify(jtproject=serialized_project)


@jtui.route('/get_available_jtmodules')
# @jwt_required()
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
    repo_location = current_app.config.get('JTUI_REPO_DIR_LOCATION')
    if repo_location is None:
        raise Exception(
            'You have to set the config`JTUI_REPO_DIR_LOCATION` to the '
            ' location of the Jterator modules.'
        )
    modules = AvailableModules(repo_location)
    return jsonify(jtmodules=modules.as_dict())


@jtui.route('/get_available_jtpipelines')
# @jwt_required()
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
        for p in list_projects(os.path.join(current_app.config.get('JTUI_REPO_DIR_LOCATION'), 'pipes'))
    ]
    pipes = []
    return jsonify(jtpipelines=pipes)


@jtui.route('/get_available_channels/<path:experiment_id>')
# @jwt_required()
def get_available_channels(experiment_id):
    '''Lists all channels for a given experiment.

    Parameters
    ----------
    experiment_id: int
        ID of the processed experiment

    Returns
    -------
    str
       JSON string with "channels" key. The corresponding value is the list of
       layer names that are available for the given experiment
    '''
    with tm.utils.Session() as session:
        channels = session.query(tm.Channel).\
            filter_by(experiment_id=experiment_id).\
            all()
        return jsonify(channels=[c.name for c in channels])


@jtui.route('/get_module_source_code/<path:module_name>')
# @jwt_required()
def get_module_source_code(module_name):
    '''Gets the source code for a given module.

    Parameters
    ----------
    module_name: str
        name of the module

    Returns
    -------
    str
       content of the module source code file
    '''
    modules = AvailableModules(current_app.config.get('JTUI_REPO_DIR_LOCATION'))
    files = [
        f for i, f in enumerate(modules.module_files)
        if modules.module_names[i] == module_name
    ]
    if len(files) == 1:
        return send_file(files[0])

@jtui.route('/get_module_figure/<path:experiment_id>/<path:pipeline_name>/<path:module_name>/<path:job_id>')
# @jwt_required()
def get_module_figure(experiment_id, pipeline_name, module_name, job_id):
    '''Gets the figure for a given module.

    Parameters
    ----------
    experiment_id: int
        ID of the processed experiment
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
        experiment_id=experiment_id,
        verbosity=logging.INFO,
        pipeline=pipeline_name,
    )
    fig_file = [
        m.build_figure_filename(jt.figures_location, int(job_id))
        for m in jt.pipeline if m.name == module_name
    ][0]
    # if os.path.exists(fig_file):
    #     figure = build_html_figure_string(fig_file)
    # else:
    #     figure = \
    #         '''
    #         <html>
    #             <body>
    #             </body>
    #         </html>
    #         '''
    return send_file(fig_file)


@jtui.route('/create_joblist', methods=['POST'])
# @jwt_required()
def create_joblist():
    '''Creates joblist for the current project and return it.

    Returns
    -------
    str
        JSON string with "joblist" key
    '''
    data = json.loads(request.data)
    data = yaml.load(data['jtproject'])
    experiment_id = data['experiment_id']
    jt = ImageAnalysisPipeline(
        experiment_id=experiment_id,
        verbosity=logging.INFO,
        pipeline=pipeline,
    )
    batch_args = get_step_args('jterator')[0]
    batches = jt.create_batches(batch_args)
    metadata = list()
    try:
        with tm.utils.Session() as session:
            metadata = dict()
            for batch in batches:
                file_ids = flatten(batch['image_file_ids'].values())
                channel_files = session.query(tm.ChannelImage).\
                    filter(tm.ChannelImage.id.in_(channel_ids)).\
                    all()
                for f in channel_files:
                    metadata[batch['id']] = {
                        'tpoint': f.tpoint,
                        'zplane': f.zplane,
                        'channel': f.channel.index,
                        'well': f.site.well.name,
                        'plate': f.site.well.plate.name
                    }
            return jsonify({'joblist': metadata})
    except Exception, e:
        error = str(e)
        print 'Error upon joblist creation: ', error
        return jsonify({'joblist': None, 'error': error})


@jtui.route('/save_jtproject', methods=['POST'])
# @jwt_required()
def save_jtproject():
    '''Saves modifications of the pipeline and module descriptions to the
    corresponding `.pipe` and `.handles` files.
    '''
    data = json.loads(request.data)
    data = yaml.load(data['jtproject'])
    experiment_id = data['experiment_id']
    jt = ImageAnalysisPipeline(
        experiment_id=experiment_id,
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


@jtui.route('/check_jtproject', methods=['POST'])
# @jwt_required()
def check_jtproject():
    '''Checks pipeline and module descriptions.
    '''
    data = json.loads(request.data)
    data = yaml.load(data['jtproject'])
    experiment_id = data['experiment_id']
    jt = ImageAnalysisPipeline(
        experiment_id=experiment_id,
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


@jtui.route('/remove_jtproject', methods=['POST'])
# @jwt_required()
def remove_jtproject():
    '''Removes `.pipe` and `.handles` files from a given Jterator project.

    Returns
    -------
    str
        JSON object with keys "success" and "error"
    '''
    data = json.loads(request.data)
    data = yaml.load(data['jtproject'])
    experiment_id = data['experiment_id']
    jt = ImageAnalysisPipeline(
        experiment_id=experiment_id,
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


@jtui.route('/create_jtproject', methods=['POST'])
# @jwt_required()
def create_jtproject():
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
    experiment_id = data['experiment_id']
    jt = ImageAnalysisPipeline(
        experiment_id=experiment_id,
        verbosity=1,
        pipeline=data['name'],
        pipe=data['pipe'],
        handles=data['handles'],
    )
    # Create the project, i.e. create a folder that contains a .pipe file and
    # handles subfolder with .handles files
    if data.get('skeleton', None):
        skel_dir = os.path.join(
            current_app.config.get('JTUI_REPO_DIR_LOCATION'), 'pipes', data['skeleton']
        )
    else:
        skel_dir = None
    jt.project.create(repo_dir=current_app.config.get('JTUI_REPO_DIR_LOCATION'), skel_dir=skel_dir)
    serialized_jtproject = yaml.safe_dump(jt.project.as_dict())
    return jsonify(jtproject=serialized_jtproject)


@jtui.route('/kill', methods=['POST'])
# @jwt_required()
def kill_jobs():
    '''Kills submitted jobs.

    Returns
    -------
    str
        JSON object with keys "success" and "error"
    '''
    data = json.loads(request.data)
    persistent_id = data['taskId']
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


def _get_output(jobs, log_dir, figures_dir, module_names):
    output = list()
    for task in jobs.iter_workflow():
        if not isinstance(task, gc3libs.workflow.ParallelTaskCollection):
            continue
        for subtask in task.iter_tasks():
            if not isinstance(subtask, gc3libs.Application):
                continue
            j = int(re.search(r'_(\d+)$', subtask.jobname).group(1))
            stdout_file = os.path.join(subtask.output_dir, subtask.stdout)
            if os.path.exists(stdout_file):
                stdout = open(stdout_file).read()
            else:
                stdout = ''
            stderr_file = os.path.join(subtask.output_dir, subtask.stderr)
            if os.path.exists(stderr_file):
                stderr = open(stderr_file).read()
            else:
                stderr = ''
            if not stdout and not stderr:
                log = '-- Job is still running --'
            else:
                log = stdout + '\n' + stderr
            # Obtain the output of the individual modules in the pipeline
            # of the current jobs (stdout, stderr, and figure)
            stdout_files = glob.glob(
                os.path.join(log_dir, '*_%.5d.out' % j)
            )
            stderr_files = glob.glob(
                os.path.join(log_dir, '*_%.5d.err' % j)
            )
            fig_files = glob.glob(
                os.path.join(figures_dir, '*_%.5d.json' % j)
            )
            # Produce thumbnails for html figures by screen capture.
            # Depends on the phantomjs library and the "rasterize.js" script.
            # Needs the environment variable "RASTERIZEDIR", e.g. for homebrew
            # installation on OSX:
            # export RASTIZEDIR=/usr/local/Cellar/phantomjs/2.1.1/share/phantomjs/examples
            # if 'RASTERIZEDIR' not in os.environ:
            #     logger.warn('"RASTERIZEDIR" environment variable not set')
            # rasterize_dir = os.path.expandvars('$RASTERIZEDIR')
            # if not os.path.exists(rasterize_dir):
            #     logger.warn('"phantomjs" is not properly installed')
            # else:
            #     rasterize_file = os.path.join(rasterize_dir, 'rasterize.js')
            #     for html_file in fig_files:
            #         png_file = re.sub(r'(.*)\.html$', r'\1.png', html_file)
            #         if not os.path.exists(png_file):
            #             subprocess.call([
            #                 'phantomjs', rasterize_file, html_file, png_file
            #             ])
            # thumbnail_files = glob.glob(
            #     os.path.join(figures_dir, '*_%.5d.png' % j)
            # )
            r = re.compile('(.*)_\d+\.')
            # We need to loop over the names from the output files,
            # because some module names may not be present in case of error
            module_file = [
                re.match(r, os.path.basename(f)).group(1)
                for f in stdout_files
            ]
            module_stdout = dict(zip(
                module_file, [open(f).read() for f in stdout_files])
            )
            module_stderr = dict(zip(
                module_file, [open(f).read() for f in stderr_files])
            )
            fig_names = [
                re.match(r, os.path.basename(f)).group(1)
                for f in fig_files
            ]
            # thumbnail_names = [
            #     re.match(r, os.path.basename(f)).group(1)
            #     for f in thumbnail_files
            # ]
            # figures = dict(zip(fig_names, fig_files))
            # thumbnails = dict(zip(thumbnail_names, thumbnail_files))
            module_output = list()
            for i, m in enumerate(module_names):
                module_output.append(dict())
                module_output[i]['name'] = m
                module_output[i]['stdout'] = module_stdout.get(m, None)
                module_output[i]['stderr'] = module_stderr.get(m, None)
                # TODO: only send figures if requested, i.e. when user clicks
                # if m in thumbnails.keys():
                #     module_output[i]['thumbnail'] = build_html_figure_string(
                #                                     thumbnails.get(m, None)
                #     )
                # else:
                #     # TODO: PNG as base64
                #     module_output[i]['thumbnail'] = \
                #         '''
                #         <html>
                #             <body>
                #             </body>
                #         </html>
                #         '''
            with tm.utils.Session() as session:
                task_info = session.query(tm.Task).get(subtask.persistent_id)
                exitcode = task_info.exitcode
                submission_id = task_info.submission_id
            failed = exitcode != 0
            output.append({
                'id': j,
                'submissionId': submission_id,
                'name': subtask.jobname,
                'log': log,
                'modules': module_output,
                'failed': failed
            })
    return output


@jtui.route('/get_output', methods=['POST'])
# @jwt_required()
def get_output():
    '''Gets output generated by a previous submission.

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
    experiment_id = data['experiment_id']
    jt = ImageAnalysisPipeline(
        experiment_id=experiment_id,
        verbosity=1,
        pipeline=data['name'],
        pipe=data['pipe'],
        handles=data['handles'],
    )
    module_names = list_module_names(data['pipe']['description']['pipeline'])
    session = jt.create_gc3pie_session()
    submission_ids = natsorted(session.list_ids())
    try:
        task = session.load(submission_ids[-1])
        output = _get_output(
            task, jt.module_log_location, jt.figures_location, module_names
        )
        return jsonify(output=output)
    except IndexError:
        return jsonify({'output': None})
    except Exception as e:
        error = str(e)
        print 'Error upon output retrieval:', error
        return jsonify({'output': None, 'error': error})


def run_ui_job(data):
    '''Runs one or more jobs of the current project with pipeline and module
    descriptions provided by the UI.

    The jobs are submitted via GC3Pie, which will call the Jterator `run`
    method via the command line. This requires the pipeline and module
    descriptions to be saved to the *pipe* and *handles* files, respectively,
    and the batches written to the *jobs* file.

    The submitted jobs will be monitored while they are processed on the
    cluster and the results will be read from disk and returned to the client
    once all jobs are terminated.

    Parameters
    ----------
    data: dict
        "job" id and "jtproject" description
    '''
    # TODO: return status to the client: new, submitted, running, terminated
    job_ids = map(int, data['jobIds'])
    data = yaml.load(data['jtproject'])
    # TODO: sometimes the check fails, although the description seems fine,
    # could it be related to the "hashkey" stuff that javascript adds to the
    # JSON object?
    experiment_id = data['experiment_id']
    jt = ImageAnalysisPipeline(
        experiment_id=experiment_id,
        verbosity=1,
        pipeline=data['name'],
        pipe=data['pipe'],
        handles=data['handles'],
    )
    # Remove figure and module log files of previous run
    # to prevent accumulation of data
    jt.delete_previous_job_output()

    # 1. Save the project to disk,
    # i.e. write pipeline and module descriptions to the corresponding files
    jt.project.save()
    batch_args_cls, submit_args_cls, _ = get_step_args('jterator')
    # 3. Build jobs
    batch_args = batch_args_cls()
    submit_args = submit_args_cls()
    if job_ids:
        batch_args.plot = True
        # In "run" mode only a few selected jobs will be submitted
        job_descriptions = jt.create_batches(batch_args, job_ids)
    else:
        # In "submit" mode all jobs will be submitted
        batch_args.plot = False
        job_descriptions = jt.create_batches(batch_args)
    jt.write_batch_files(job_descriptions)
    step = jt.create_step()
    jobs = jt.create_jobs(
        step=step,
        batches=job_descriptions,
        duration=submit_args.duration,
        memory=submit_args.memory,
        cores=submit_args.cores
    )

    # 4. Add jobs to session to make them persistent on disk
    # session.remove(data['previousSubmissionId'])
    session = jt.create_gc3pie_session()
    persistent_id = session.add(jobs)
    session.save(persistent_id)

    # 5. Submit jobs
    logger.info('add jobs to engine')
    task = session.load(persistent_id)
    logger.info('submitted GC3Pie task: %s', persistent_id)
    engine.add(task)

    tasks[persistent_id] = task

    # 6. Monitor job status
    module_names = list_module_names(data['pipe']['description']['pipeline'])
    break_next = False
    while True:

        time.sleep(5)

        if break_next:
            break

        task_data = cluster_utils.get_task_data_from_engine(task)
        cluster_utils.print_task_status(task_data, monitoring_depth=2)

        # break out of the loop when all jobs are done
        if task_data['is_done']:
            break_next = True

        # send status report to client
        socket.send(
            json.dumps({
                'event': 'status',
                'data': task_data
            })
        )
        # send output (log and figures) to client
        socket.send(
            json.dumps({
                'event': 'output',
                'data': _get_output(
                    task, jt.module_log_location, jt.figures_location,
                    module_names
                )
            })
        )


# @websocket.route('/socket')
# def listen(ws):
#     while True:
#         msg_str = ws.receive()
#         if msg_str:
#             msg = json.loads(msg_str)

#             event = msg['event']

#             data = msg['data']

#             if event == 'register':
#                 print '\n--- REGISTER TOOL INSTANCE FOR WEBSOCKET ---\n'
#                 global socket
#                 socket = ws
#                 # TODO: multiple sockets, one per user
#                 # How do we limit the user to go crazy? For example, in case
#                 # user would have several taps, browser windows open and clicks
#                 # around like hell.
#                 # then we just create one engine per user (during the login)
#                 # and we fetch the engine during job monitoring (while loop)
#             elif event == 'run':
#                 print '\n--- RUN JOB ---\n'
#                 run_ui_job(data)
#             else:
#                 print 'Unknown event: ' + event


# # @jtui.route('/help/<path:module_filename>')
# # def module_help(module_filename):
# #     try:
# #         return send_from_directory(lcfg.REPO_LOCATION, 'modules',
# #                                    module_filename)
# #     except Exception as e:
# #         return jsonify({'error': str(e)})

# # TODO: module help should link to Read the Docs
#  # error and figure for each module and send it
#         #   to the client

