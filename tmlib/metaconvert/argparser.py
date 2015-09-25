from . import __version__
from .cli import Metaconvert


parser, subparsers = Metaconvert.get_parser_and_subparsers()

parser.description = '''
        Convert OMEXML metadata extracted from image files to a custom format
        and complement missing information with additional metadata or optional
        user input.
    '''
parser.version = __version__
parser.add_argument(
    '-f', '--format', type=str, default=None,
    help='microscope-specific file format')

for name in subparsers.choices:
    subparsers.choices[name].set_defaults(handler=Metaconvert.call)
