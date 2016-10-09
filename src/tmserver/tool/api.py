import os
import json
import logging
from flask import jsonify, request, current_app
from flask_jwt import jwt_required
from flask.ext.jwt import current_identity

import tmlib.models as tm
from tmlib.writers import JsonWriter

from tmserver.api import api
from tmserver.error import (
    MalformedRequestError,
    ResourceNotFoundError,
    NotAuthorizedError
)
from tmserver.util import decode_query_ids, decode_form_ids
from tmserver.util import assert_query_params, assert_form_params
from tmserver.tool.job import ToolJob
from tmserver.extensions import gc3pie

from tmtoolbox.session import ToolSession
from tmtoolbox.result import ToolResult, LabelLayer
from tmtoolbox import SUPPORTED_TOOLS
from tmtoolbox import get_tool_class


logger = logging.getLogger(__name__)


def _create_mapobject_feature(mapobject_id, geometry_description):
    """Creates a GeoJSON feature for the given mapobject and GeoJSON geometry.

    Parameters
    ----------
    mapobject_id: int
        ID of the mapobject
    geometry_description: XXX
        description of a GeoJSON geometry

    Returns
    -------
    dict
    """
    return {
        'type': 'Feature',
        'geometry': geometry_description,
        'properties': {
            'id': str(mapobject_id)
        }
    }


@api.route('/tools', methods=['GET'])
@jwt_required()
def get_tools():
    tool_descriptions = list()
    for name in SUPPORTED_TOOLS:
        tool_cls = get_tool_class(name)
        tool_descriptions.append({
            'name': tool_cls.__name__,
            'icon': tool_cls.__icon__,
            'description': tool_cls.__description__,
            'methods': getattr(tool_cls, '__methods__', [])
        })
    return jsonify(data=tool_descriptions)


@api.route(
    '/experiments/<experiment_id>/tools/request', methods=['POST']
)
@jwt_required()
@decode_query_ids()
@assert_form_params('payload', 'session_uuid', 'tool_name')
def process_tool_request(experiment_id):
    """Processes a generic tool request sent by the client.
    POST payload should have the format:

    {
        payload: dict,
        session_uuid: str
    }

    Returns:

    {
        return_value: object
    }

    """
    data = request.get_json()
    payload = data.get('payload', {})
    session_uuid = data.get('session_uuid')
    tool_name = data.get('tool_name')

    # Instantiate the correct tool plugin class.
    logger.info('process request of tool "%s"', tool_name)

    with tm.utils.MainSession() as session:
        experiment = session.query(tm.ExperimentReference).get(experiment_id)
        user_name = experiment.user.name
        tool_dir = os.path.join(experiment.tools_location, tool_name)
        submission = tm.Submission(experiment_id, program='tool')
        session.add(submission)
        session.flush()
        submission_id = submission.id

    tool_log_dir = os.path.join(tool_dir, 'logs')
    tool_batch_dir = os.path.join(tool_dir, 'batches')
    if not os.path.exists(tool_log_dir):
        os.makedirs(tool_log_dir)
    if not os.path.exists(tool_batch_dir):
        os.makedirs(tool_batch_dir)

    with tm.utils.ExperimentSession(experiment_id) as session:
        session = session.get_or_create(ToolSession, uuid=session_uuid)
        session_id = session.id

    batch_filename = '%s_%d.json' % (tool_name, session_id)
    batch_location = os.path.join(tool_batch_dir, batch_filename)
    with JsonWriter(batch_location) as f:
        f.write(payload)

    # Create and submit tool job for asynchronous processing on the cluster
    if cfg.use_spark:
        args = ['spark-submit', '--master', cfg.spark_master]
        if cfg.spark_master == 'yarn':
            args.extend(['--deploy-mode', 'client'])
        # TODO: ship Python dependencies
        # args.extend([
        #     '--py-files', cfg.spark_tmtoolbox_egg
        # ])
    else:
        args = []
    args.extend([
        'tmtool', str(experiment_id),
        '--tool', tool_name,
        '--submission_id', str(submission_id),
        '--batch_file', batch_location,
    ])
    if cfg.use_spark:
        args.append('--use_spark')

    job = ToolJob(
        tool_name=tool_name,
        arguments=args,
        output_dir=tool_log_dir,
        submission_id=submission_id,
        user_name=user_name
    )
    gc3pie.store_jobs(job)
    gc3pie.submit_jobs(job)

    return jsonify(message='ok')


@api.route(
    '/experiments/<experiment_id>/tools/result', methods=['GET']
)
@decode_query_ids()
@assert_query_params('submission_id')
def get_tool_result(experiment_id):
    submission_id = request.args.get('submission_id', type=int)
    logger.info('get tool result for submission %d', submission_id)
    with tm.utils.ExperimentSession(experiment_id) as session:
        tool_result = session.query(ToolResult).\
            filter_by(submission_id=submission_id).\
            one()
        return jsonify(data=tool_result)


@api.route(
    '/experiments/<experiment_id>/tools/status', methods=['GET']
)
@decode_query_ids()
def get_tool_job_status(experiment_id):
    logger.info('get status of tool jobs for experiment %d', experiment_id)
    with tm.utils.MainSession() as session:
        tool_job_status_ = session.query(
                tm.Task.state, tm.Task.submission_id, tm.Task.exitcode
            ).\
            join(tm.Submission).\
            filter(
                tm.Submission.program == 'tool',
                tm.Submission.experiment_id == experiment_id
            ).\
            all()
        tool_job_status = \
            [{'state': st[0], 'submission_id': st[1], 'exitcode': st[2]}
             for st in tool_job_status_]

        return jsonify(data=tool_job_status)


@api.route(
    '/experiments/<experiment_id>/labellayers/<label_layer_id>/tiles',
    methods=['GET']
)
@decode_query_ids()
@assert_query_params('x', 'y', 'z', 'zplane', 'tpoint')
def get_label_layer_tiles(experiment_id, label_layer_id):
    """Get all mapobjects together with the labels that were assigned to them
    for a given tool result and tile coordinate.

    """
    # The coordinates of the requested tile
    x = request.args.get('x', type=int)
    y = request.args.get('y', type=int)
    z = request.args.get('z', type=int)
    zplane = request.args.get('zplane', type=int)
    tpoint = request.args.get('tpoint', type=int)

    with tm.utils.ExperimentSession(experiment_id) as session:
        label_layer = session.query(LabelLayer).get(label_layer_id)
        logger.info('get result tiles for label layer "%s"', label_layer.type)
        mapobject_type = session.query(tm.MapobjectType).\
            get(label_layer.mapobject_type_id)
        query_res = mapobject_type.get_mapobject_outlines_within_tile(
            x, y, z, zplane=zplane, tpoint=tpoint
        )

        features = []
        has_mapobjects_within_tile = len(query_res) > 0

        if has_mapobjects_within_tile:
            mapobject_ids = [c[0] for c in query_res]
            mapobject_id_to_label = label_layer.get_labels(mapobject_ids)

            features = [
                {
                    'type': 'Feature',
                    'geometry': json.loads(geom_geojson_str),
                    'properties': {
                        'label': mapobject_id_to_label[id],
                        'id': id
                     }
                }
                for id, geom_geojson_str in query_res
            ]

        return jsonify({
            'type': 'FeatureCollection',
            'features': features
        })

