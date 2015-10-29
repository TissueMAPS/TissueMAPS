'''
Arguments of the command line program.
'''

from . import __version__
from .cli import Align

parser, subparsers = Align.get_parser_and_subparsers(
    required_subparsers=[
        'init', 'run', 'submit', 'apply', 'collect', 'cleanup'])

parser.description = '''
    Calculate shift in y, x direction for images, which were
    acquired in different "cycles", i.e. at different time points.
'''
parser.version = __version__

init_parser = subparsers.choices['init']
init_parser.add_argument(
    '-b', '--batch_size', dest='batch_size', type=int, default=5,
    help='number of image files that should be registered per job '
         '(default: 5)')

init_registration_group = init_parser.add_argument_group(
    'additional arguments for image registration')
init_registration_group.add_argument(
    '--ref_cycle', type=int, required=True,
    help='zero-based index of the reference cycle')
init_registration_group.add_argument(
    '--ref_channel', type=int, required=True,
    help='zero-based index of the reference channel')
init_registration_group.add_argument(
    '-l', '--limit', type=int, default=300,
    help='shift limit, i.e. maximally allowed shift in pixels (default: 300)')

apply_parser = subparsers.choices['apply']
apply_parser.add_argument(
    '-i', '--illumcorr', action='store_true',
    help='also correct images for illumination artifacts')

for name in subparsers.choices:
    subparsers.choices[name].set_defaults(handler=Align.call)
