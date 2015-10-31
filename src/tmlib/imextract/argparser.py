'''
Arguments of the command line program.
'''

from . import __version__
from .cli import Imextract
from .args import ImextractInitArgs


parser, subparsers = Imextract.get_parser_and_subparsers()

parser.description = '''
    Extract images from heterogeneous microscopic image file formats
    and store each 2D plane in a separate PNG file.
'''
parser.version = __version__

init_parser = subparsers.choices['init']
init_extra_group = init_parser.add_argument_group(
    'additional program-specific arguments')
ImextractInitArgs().add_to_argparser(init_extra_group)

for name in subparsers.choices:
    subparsers.choices[name].set_defaults(handler=Imextract.call)
