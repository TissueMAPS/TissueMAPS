from . import __version__
from .cli import Align


parser, subparsers = Align.get_parser_and_subparsers(
                        required_subparsers=[
                            'run', 'joblist', 'submit', 'apply', 'collect',
                            'workflow'
                        ])

parser.description = '''
        Calculate shift in y,x direction for images, which were
        acquired in different "cycles", i.e. at the same sites but at
        different time points.
    '''
parser.version = __version__

joblist_parser = subparsers.choices['joblist']
joblist_parser.add_argument(
    '-b', '--batch_size', dest='batch_size', type=int, default=10,
    help='number of image files that should be processed per job')
joblist_parser.add_argument(
        '--ref_cycle', type=str, required=True,
        help='name of the reference cycle')
joblist_parser.add_argument(
        '--ref_channel', type=str, required=True,
        help='name of the reference channel')

collect_parser = subparsers.choices['collect']
collect_parser.add_argument(
        '-m', '--max_shift', type=int, default=100,
        help='maximally tolerated shift in pixels (defaults to 100)')

for name in subparsers.choices:
    subparsers.choices[name].set_defaults(handler=Align.call)
