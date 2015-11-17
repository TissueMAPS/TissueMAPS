'''
Arguments of the command line program.
'''

from . import __version__
from .cli import Tmaps
from .args import TmapsSubmitArgs


parser, subparsers = Tmaps.get_parser_and_subparsers()

parser.description = '''
    Build a TissueMAPS workflow, submit it to the cluster, and
    monitor its processing.
'''
parser.version = __version__

submit_parser = subparsers.choices['submit']
submit_extra_group = submit_parser.add_argument_group(
    'additional workflow-specific arguments')
TmapsSubmitArgs().add_to_argparser(submit_extra_group)

for name in subparsers.choices:
    subparsers.choices[name].set_defaults(handler=Tmaps.call)
