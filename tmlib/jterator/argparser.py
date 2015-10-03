from . import __version__
from .cli import Jterator


parser, subparsers = Jterator.get_parser_and_subparsers(
    required_subparsers=[
        'init', 'run', 'submit', 'kill', 'collect', 'cleanup'
    ])

parser.description = '''
    Image analysis pipeline engine for applying a sequence of algorithms
    to a set of images, for example for segmentation and feature extraction.
'''
parser.version = __version__
parser.add_argument(
    '-p', '--pipeline', dest='pipeline', type=str, required=True,
    help='name of a pipeline that should be processed')

create_parser = subparsers.add_parser(
    'create',
    help='create a new project')
create_parser.description = '''
    Create a new jterator project on disk.
'''
create_parser.add_argument(
    '--repo_dir', type=str, default=None,
    help='path to repository directory where module files are located')
create_parser.add_argument(
    '--skel_dir', type=str, default=None,
    help='path to repository directory that represents a project skeleton')

remove_parser = subparsers.add_parser(
    'remove',
    help='remove an existing project')
remove_parser.description = '''
    Remove an existing jterator project on disk.\n
    WARNING: This will also remove any project related data!
'''

check_parser = subparsers.add_parser(
    'check',
    help='check descriptor files')
check_parser.description = '''
    Check content of the .pipe and .handles files descriptor files.
'''

for name in subparsers.choices:
    subparsers.choices[name].set_defaults(handler=Jterator.call)
