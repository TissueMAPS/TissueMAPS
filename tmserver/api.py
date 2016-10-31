"""
Module to import all view functions such that they are registered with the
appropriate blueprint.

"""
from flask import Blueprint

api = Blueprint('api', __name__)

import tmserver.experiment.api
import tmserver.experiment.upload
import tmserver.tool.api
import tmserver.user.api
import tmserver.mapobject.api
import tmserver.error
