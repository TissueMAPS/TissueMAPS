'''
Parse arguments from the command line.
'''

from .cli import Align
from .args import AlignInitArgs
from .args import AlignApplyArgs
from ..args import ApplyArgs

parser, subparsers = Align.get_parser_and_subparsers()

parser.description = '''
    Calculate shift in y, x direction between images, which were
    acquired in different "cycles", i.e. at different time points.
'''

init_parser = subparsers.choices['init']
init_extra_group = init_parser.add_argument_group(
    'additional step-specific arguments')
AlignInitArgs().add_to_argparser(init_extra_group)

apply_parser = subparsers.add_parser(
    'apply', help='apply job output')
apply_parser.description = '''
    Apply calculated shift statistics to (a subset of) images
    in order to align them between cycles.
'''
ApplyArgs().add_to_argparser(apply_parser)

apply_extra_group = apply_parser.add_argument_group(
    'additional step-specific arguments')
AlignApplyArgs().add_to_argparser(apply_extra_group)

for name in subparsers.choices:
    subparsers.choices[name].set_defaults(handler=Align.call)
