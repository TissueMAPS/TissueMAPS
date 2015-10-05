from . import __version__
from .cli import Metaconvert
from ..formats import Formats


parser, subparsers = Metaconvert.get_parser_and_subparsers()

parser.description = '''
        Convert metadata extracted from image files to a custom format
        and complement it with additional information.
    '''
parser.version = __version__

init_parser = subparsers.choices['init']
init_parser.add_argument(
    '-f', '--format', type=str, default=None,
    choices=Formats.SUPPORT_FOR_ADDITIONAL_FILES,
    help='microscope-specific file format')

for name in subparsers.choices:
    subparsers.choices[name].set_defaults(handler=Metaconvert.call)
