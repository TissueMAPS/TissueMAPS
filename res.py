"""
This ist just a small module for development purposes that provides routes to
serve the files. This should later be done directly via NGINX or some other
full web server.

"""

from os.path import join
from flask import current_app, Blueprint, send_file, send_from_directory
from flask_jwt import jwt_required

from appfactory import EXPDATA_DIR_LOCATION


res = Blueprint('res', __name__)


@res.route('/expdata/<path:filename>')
# @jwt_required() # TODO: Why isn't this working?
def expdata_file(filename):
    # TODO:
    # Check here if the user does have access for this file.
    # If yes, use send_file (with X-Sendfile == True) to send the file.
    print filename
    return send_from_directory(EXPDATA_DIR_LOCATION, filename)


@res.route('/')
def app_index():
    """
    Serve the index file (the initial `empty` html file that will be filled in
    by Angular).
    """
    static_folder = current_app.static_folder
    print static_folder
    return send_file(join(static_folder, 'index.html'))


@res.route('/tools/')
def tool_index(filename=''):
    """
    Serve the index file (the initial `empty` html file that will be filled in
    by Angular).
    """
    return send_file(join(current_app.static_folder,
                          'templates', 'tools', 'index.html'))
