from . import __version__
from .cli import Metaextract


parser, subparsers = Metaextract.get_parser_and_subparsers(
    required_subparsers=['init', 'submit', 'kill', 'collect', 'cleanup'])

parser.description = '''
        Extract OMEXML metadata from heterogeneous microscopic image file
        formats using Bio-Formats.
    '''
parser.version = __version__

for name in subparsers.choices:
    subparsers.choices[name].set_defaults(handler=Metaextract.call)
