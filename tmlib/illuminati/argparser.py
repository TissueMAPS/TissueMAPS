from . import __version__
from .cli import Illuminati


parser, subparsers = Illuminati.get_parser_and_subparsers(
                        required_subparsers=['run', 'joblist', 'submit'])

parser.description = '''
        Create image pyramids for zoom visualization in TissueMAPS.
    '''
parser.version = __version__

joblist_parser = subparsers.choices['joblist']
joblist_parser.add_argument(
    '-s', '--shift', action='store_true',
    help='shift stitched image')
joblist_parser.add_argument(
    '-i', '--illumcorr', action='store_true',
    help='correct images for illumination artifacts before stitching')
joblist_parser.add_argument(
    '-t', '--thresh', action='store_true',
    help='rescale pixel values between min value and a threshold level')
joblist_parser.add_argument(
    '--thresh_value', type=int, default=None,
    help='fixed pixel value for threshold')
joblist_parser.add_argument(
    '--thresh_percent', type=float, default=9.99,
    help='percentage of pixel values below threshold (defaults to 99.99)')

for name in subparsers.choices:
    subparsers.choices[name].set_defaults(handler=Illuminati.call)
