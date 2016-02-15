'''
Arguments of the command line program.
'''

from . import __version__
from .cli import Illuminati
from .args import IlluminatiInitArgs


parser, subparsers = Illuminati.get_parser_and_subparsers(
    required_subparsers=['init', 'run', 'submit', 'cleanup', 'log', 'info'])

parser.description = '''
        Create image pyramids for visualization in TissueMAPS.
    '''
parser.version = __version__

init_parser = subparsers.choices['init']
init_extra_group = init_parser.add_argument_group(
    'additional step-specific arguments')
IlluminatiInitArgs().add_to_argparser(init_extra_group)

for name in subparsers.choices:
    subparsers.choices[name].set_defaults(handler=Illuminati.call)
