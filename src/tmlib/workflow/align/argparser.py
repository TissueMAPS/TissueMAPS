'''
Parse arguments from the command line.
'''

from tmlib.workflow.align.cli import Align
from tmlib.workflow.align.args import AlignInitArgs

parser, subparsers = Align.get_parser_and_subparsers()

parser.description = '''
    Calculate shift in y, x direction between images, which were
    acquired in different "cycles", i.e. at different time points.
'''

init_parser = subparsers.choices['init']
init_extra_group = init_parser.add_argument_group(
    'additional step-specific arguments')
AlignInitArgs().add_to_argparser(init_extra_group)

for name in subparsers.choices:
    subparsers.choices[name].set_defaults(call=Align.call)
