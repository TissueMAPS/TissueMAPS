from . import __version__
from .cli import Tmaps

parser, subparsers = Tmaps.get_parser_and_subparsers()

parser.description = '''
        Build and manage TissueMAPS workflows.
    '''
parser.version = __version__

for name in subparsers.choices:
    subparsers.choices[name].set_defaults(handler=Tmaps.call)
