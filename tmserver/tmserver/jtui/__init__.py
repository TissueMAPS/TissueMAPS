import logging
from flask import Blueprint


jtui = Blueprint('jtui', __name__)

logger = logging.getLogger(__name__)

import tmserver.jtui.api


