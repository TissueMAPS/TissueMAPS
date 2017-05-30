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
"""API view functions for querying :mod:`file <tmlib.models.file>` resources.
"""
import json
import logging
from flask import jsonify, send_file, request
from flask_jwt import jwt_required
from cStringIO import StringIO
from werkzeug import secure_filename

import tmlib.models as tm

from tmserver.util import (
    decode_query_ids, decode_form_ids, is_true, is_false,
    assert_query_params, assert_form_params
)
from tmserver.api import api
from tmserver.error import *


logger = logging.getLogger(__name__)


@api.route(
    '/experiments/<experiment_id>/channels/<channel_id>/image-file',
    methods=['GET']
)
@jwt_required()
@assert_query_params(
    'plate_name', 'cycle_index', 'well_name', 'well_pos_x', 'well_pos_y',
    'tpoint', 'zplane'
)
@decode_query_ids('read')
def get_channel_image_file(experiment_id, channel_id):
    """
    .. http:get:: /api/experiments/(string:experiment_id)/channels/(string:channel_id)/image-files

        Get a specific image belonging to a channel.

        **Example response**:

        .. sourcecode:: http

            HTTP/1.1 200 OK
            Content-Type: image/png

        :query plate_name: name of the plate (required)
        :query cycle_index: cycle's index (required)
        :query well_name: name of the well (required)
        :query well_pos_x: x-coordinate of the site within the well (optional)
        :query well_pos_y: y-coordinate of the site within the well (optional)
        :query tpoint: time point (required)
        :query zplane: z-plane (required)
        :query illumcorr: correct image for illumination artifacts (optional)
        :query align: align image relative to reference cycle (optional)

        :reqheader Authorization: JWT token issued by the server
        :statuscode 200: no error
        :statuscode 404: no matching image found
        :statuscode 400: not all query parameters provided

    """
    logger.info(
        'get image of channel %d from experiment %d', channel_id, experiment_id
    )
    plate_name = request.args.get('plate_name')
    well_name = request.args.get('well_name')
    x = request.args.get('well_pos_x', type=int)
    y = request.args.get('well_pos_y', type=int)
    cycle_index = request.args.get('cycle_index', type=int)
    tpoint = request.args.get('tpoint', type=int)
    zplane = request.args.get('zplane', type=int)
    illumcorr = is_true(request.args.get('correct'))
    align = is_true(request.args.get('align'))
    with tm.utils.MainSession() as session:
        experiment = session.query(tm.ExperimentReference).get(experiment_id)
        experiment_name = experiment.name
    with tm.utils.ExperimentSession(experiment_id) as session:
        site_id = session.query(tm.Site.id).\
            join(tm.Well).\
            join(tm.Plate).\
            filter(
                tm.Plate.name == plate_name,
                tm.Well.name == well_name,
                tm.Site.x == x, tm.Site.y == y
            ).\
            one()[0]
        channel = session.query(tm.Channel).get(channel_id)
        channel_name = channel.name
        image_file = session.query(tm.ChannelImageFile).\
            join(tm.Cycle).\
            filter(
                tm.Cycle.index == cycle_index,
                tm.ChannelImageFile.site_id == site_id,
                tm.ChannelImageFile.channel_id == channel_id,
                tm.ChannelImageFile.tpoint == tpoint,
                tm.ChannelImageFile.zplane == zplane
            ).\
            one()
        img = image_file.get()
        if illumcorr:
            # TODO: cache in Redis for a limited amount of time to not having to
            # load the file repeatedly when user downloads multiple files of the
            # same channel
            logger.info('correct image for illumination artefacts')
            illumstats_file = session.query(tm.IllumstatsFile).\
                filter_by(channel_id=channel_id).\
                one_or_none()
            if illumstats_file is None:
                raise ResourceNotFoundError(
                    'No illumination statistics file found for channel %d'
                    % channel_id
                )
            stats = illumstats_file.get()
            img = img.correct(stats)
    if align:
        img = img.align()

    pixels = img.png_encode()
    f = StringIO()
    f.write(pixels)
    f.seek(0)
    filename = '%s_%s_%s_y%.3d_x%.3d_z%.3d_t%.3d_%s.png' % (
        experiment_name, plate_name, well_name, y, x, zplane, tpoint,
        channel_name
    )
    return send_file(
        f,
        attachment_filename=secure_filename(filename),
        mimetype='image/png',
        as_attachment=True
    )

