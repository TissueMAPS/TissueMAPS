'''
Arguments of the command line program.
'''

from . import __version__
from .cli import Align
from .args import AlignInitArgs
from .args import AlignApplyArgs

parser, subparsers = Align.get_parser_and_subparsers(
    required_subparsers=[
        'init', 'run', 'submit', 'apply', 'collect', 'cleanup'])

parser.description = '''
    Calculate shift in y, x direction between images, which were
    acquired in different "cycles", i.e. at different time points.
'''
parser.version = __version__

init_parser = subparsers.choices['init']
init_extra_group = init_parser.add_argument_group(
    'additional program-specific arguments')
AlignInitArgs().add_to_argparser(init_extra_group)

apply_parser = subparsers.choices['apply']
apply_parser.description = '''
    Apply calculated shift statistics to (a subset of) images
    in order to align them between cycles.
'''
apply_extra_group = apply_parser.add_argument_group(
    'additional program-specific arguments')
AlignApplyArgs().add_to_argparser(apply_extra_group)

for name in subparsers.choices:
    subparsers.choices[name].set_defaults(handler=Align.call)
