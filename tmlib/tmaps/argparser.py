from . import __version__
from .cli import Tmaps

parser, subparsers = Tmaps.get_parser_and_subparsers()

parser.description = '''
    Build a TissueMAPS workflow and submit it to the cluster.
'''
parser.version = __version__

submit_parser = subparsers.choices['submit']
submit_parser.add_argument(
    '--stage', type=str, required=True,
    help='name of the stage from where workflow should be started')
submit_parser.add_argument(
    '--step', type=str,
    help='name of the step within stage from where workflow should be started')

for name in subparsers.choices:
    subparsers.choices[name].set_defaults(handler=Tmaps.call)
