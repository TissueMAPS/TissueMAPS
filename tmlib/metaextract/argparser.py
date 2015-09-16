from . import __version__
from .cli import MetaExtract


parser, subparsers = MetaExtract.get_parser_and_subparsers(
                        required_subparsers=[
                            'joblist', 'submit', 'collect'])

parser.description = '''
        Extract metadata from heterogeneous microscopic image file formats
        using the Bio-Formats library.
    '''
parser.version = __version__

for name in subparsers.choices:
    subparsers.choices[name].set_defaults(handler=MetaExtract.call)
