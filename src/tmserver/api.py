from flask import Blueprint

api = Blueprint('api', __name__)

import tmserver.experiment.api
import tmserver.experiment.upload
import tmserver.tool.api
import tmserver.user.api
import tmserver.mapobject.api
