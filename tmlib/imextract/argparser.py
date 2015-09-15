from . import __version__
from .cli import ImExtract


parser, subparsers = ImExtract.get_parser_and_subparsers()

parser.description = '''
        Extract images from heterogeneous microscopic image file formats
        using the Bio-Formats library.
    '''
parser.version = __version__

joblist_parser = subparsers.choices['joblist']
joblist_parser.add_argument(
    '-b', '--batch_size', dest='batch_size', type=int, default=10,
    help='number of image files that should be processed per job')

for name in subparsers.choices:
    subparsers.choices[name].set_defaults(handler=ImExtract.call)
