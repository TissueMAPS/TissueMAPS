'''
Arguments of the command line program.
'''

from . import __version__
from .cli import Metaextract
from .args import MetaextractInitArgs


parser, subparsers = Metaextract.get_parser_and_subparsers(
    required_subparsers=['init', 'submit', 'collect', 'cleanup'])

parser.description = '''
        Extract OMEXML metadata from heterogeneous microscopic image file
        formats using Bio-Formats.
    '''
parser.version = __version__

init_parser = subparsers.choices['init']
init_extra_group = init_parser.add_argument_group(
    'additional program-specific arguments')
MetaextractInitArgs().add_to_argparser(init_extra_group)

for name in subparsers.choices:
    subparsers.choices[name].set_defaults(handler=Metaextract.call)
