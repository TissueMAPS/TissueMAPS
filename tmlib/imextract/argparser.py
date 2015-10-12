from . import __version__
from .cli import Imextract


parser, subparsers = Imextract.get_parser_and_subparsers()

parser.description = '''
        Extract images from heterogeneous microscopic image file formats
        and store each 2D plane in a separate PNG file.
    '''
parser.version = __version__

init_parser = subparsers.choices['init']
init_parser.add_argument(
    '-b', '--batch_size', type=int, default=10,
    help='number of image files that should be processed per job'
         '(default: 10)')

for name in subparsers.choices:
    subparsers.choices[name].set_defaults(handler=Imextract.call)
