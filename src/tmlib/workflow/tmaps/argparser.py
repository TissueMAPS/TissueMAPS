'''
Parse arguments from the command line.
'''

from tmlib.workflow.tmaps.cli import Tmaps
from tmlib.workflow.tmaps.args import TmapsSubmitArgs
from tmlib.workflow.tmaps.args import TmapsResubmitArgs


parser, subparsers = Tmaps.get_parser_and_subparsers()

parser.description = '''
    TissueMAPS workflow manager.
'''

submit_parser = subparsers.choices['submit']
submit_extra_group = submit_parser.add_argument_group(
    'additional workflow-specific arguments')
TmapsSubmitArgs().add_to_argparser(submit_extra_group)

resubmit_parser = subparsers.choices['resubmit']
resubmit_extra_group = resubmit_parser.add_argument_group(
    'additional workflow-specific arguments')
TmapsResubmitArgs().add_to_argparser(resubmit_extra_group)

for name in subparsers.choices:
    subparsers.choices[name].set_defaults(call=Tmaps.call)
