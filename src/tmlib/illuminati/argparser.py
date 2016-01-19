'''
Arguments of the command line program.
'''

from . import __version__
from .cli import Illuminati
from .args import IlluminatiInitArgs
from .args import IlluminatiRunArgs
from .args import IlluminatiLogArgs


parser, subparsers = Illuminati.get_parser_and_subparsers(
    required_subparsers=['init', 'run', 'submit', 'cleanup', 'log'])

parser.description = '''
        Create image pyramids for visualization in TissueMAPS.
    '''
parser.version = __version__

init_parser = subparsers.choices['init']
init_extra_group = init_parser.add_argument_group(
    'additional program-specific arguments')
IlluminatiInitArgs().add_to_argparser(init_extra_group)

run_parser = subparsers.choices['run']
run_extra_group = run_parser.add_argument_group(
    'additional program-specific arguments')
IlluminatiRunArgs().add_to_argparser(run_extra_group)

log_parser = subparsers.choices['log']
log_extra_group = log_parser.add_argument_group(
    'additional program-specific arguments')
IlluminatiLogArgs().add_to_argparser(log_extra_group)

for name in subparsers.choices:
    subparsers.choices[name].set_defaults(handler=Illuminati.call)
