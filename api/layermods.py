import os.path as p

from flask import jsonify, send_file
from flask_jwt import jwt_required
from flask.ext.jwt import current_user
import io
from PIL import Image
from scipy import misc as smisc

from db import db
from api import api
from models import LayerMod
from tools import get_tool


# TODO: This method should also be flagged with `@jwt_required()`.
# openlayers needs to send the token along with its request for files!
@api.route('/layermods/<int:layermod_id>/tiles/<path:filename_jpg>', methods=['GET'])
def get_modified_layer_tile(layermod_id, filename_jpg):
    """
    Send the requested tile but first pipe it through a specific layermod function.

    """
    is_authorized = True
    if is_authorized:

        layermod = LayerMod.query.get(layermod_id)
        if not layermod:
            return 'No layermod with id %d' % layermod_id,  404

        experiment = layermod.experiment

        # Openlayers requests .jpg tiles, but the source tiles are stored in
        # 16bit grayscale PNG.
        filename = filename_jpg.replace('.jpg', '.png')

        # The path to the source tile which needs to be modified
        filepath = p.join(experiment.location,
                          'layermod_src',
                          layermod.source,
                          filename)
        tool_cls = get_tool(layermod.tool_id)
        try:
            modfunc = getattr(tool_cls, layermod.tool_method_name)
        except AttributeError:
            return 'The tool with id %s has no method %s' \
                % (layermod.tool_id, layermod.tool_method_name), 400
        else:
            # Load the cell ids
            idmat_rgb = smisc.imread(filepath)
            # Convert the cell ids that were encoded as RGB back
            # into their normal representation.
            # import ipdb; ipdb.set_trace()
            idmat = idmat_rgb[:, :, 0] * 256**2 + \
                    idmat_rgb[:, :, 1] * 256 + \
                    idmat_rgb[:, :, 2]
            out = modfunc(idmat, layermod.modfunc_arg)
            # Write the image to a file descriptor and pass it to
            # flask's send_file function.
            im = Image.fromarray(out.astype('uint8'))
            # im = Image.open(filepath) # TODO: Load image from `out`
            # import ipdb; ipdb.set_trace()
            fd = io.BytesIO()
            im.save(fd, 'JPEG', quality=100)
            fd.seek(0)

            return send_file(fd, mimetype='image/jpeg')
    else:
        return 'You have no permission to access this ressource', 401


@api.route('/layermods/<int:layermod_id>', methods=['GET'])
@jwt_required()
def get_layermod(layermod_id):
    layermod = LayerMod.query.get(layermod_id)
    return jsonify(layermod.as_dict())


@api.route('/layermods/<int:layermod_id>', methods=['DELETE'])
@jwt_required()
def delete_layermod(layermod_id):
    layermod = LayerMod.query.get(layermod_id)
    if not layermod_id:
        return 'No layermod found with id %d' % layermod_id, 404
    if layermod.appstate.is_editable_by_user(current_user):
        db.session.delete(layermod)
        db.session.commit()
        return 'Layermod was removed successfully', 200
    else:
        return 'You don\'t have the permission to edit the appstate, to ' \
               'which this layermod belongs', 401

