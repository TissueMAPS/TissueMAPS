from . import __version__
from .cli import Jterator


parser, subparsers = Jterator.get_parser_and_subparsers(
                        required_subparsers=[
                            'run', 'joblist', 'submit', 'collect'])

parser.description = '''
    Image analysis pipeline engine for applying a sequence of algorithms
    to a set of images in order to segment objects and extract features
    for these objects.
'''
parser.version = __version__
parser.add_argument(
    '-p', '--pipeline', dest='pipeline', type=str, required=True,
    help='name of a pipeline that should be processed')

joblist_parser = subparsers.choices['joblist']
joblist_parser.add_argument(
    '-b', '--batch_size', dest='batch_size', type=int, default=10,
    help='number of image files that should be processed per job')

create_parser = subparsers.add_parser('create')
create_parser.add_argument(
    '--repo_dir', type=str, default=None,
    help='path to repository directory where module files are located')
create_parser.add_argument(
    '--skel_dir', type=str, default=None,
    help='path to repository directory that represents a project skeleton')

check_parser = subparsers.add_parser('check')

for name in subparsers.choices:
    subparsers.choices[name].set_defaults(handler=Jterator.call)
