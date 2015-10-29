'''
Arguments of the command line program.
'''

from . import __version__
from .cli import Illuminati


parser, subparsers = Illuminati.get_parser_and_subparsers(
    required_subparsers=['init', 'run', 'submit', 'cleanup'])

parser.description = '''
        Create image pyramids for visualization in TissueMAPS.
    '''
parser.version = __version__

init_parser = subparsers.choices['init']

init_stitch_group = init_parser.add_argument_group(
    'additional arguments for processing of the stitched mosaic image')
init_stitch_group.add_argument(
    '-s', '--shift', action='store_true',
    help='shift stitched image')
init_stitch_group.add_argument(
    '-i', '--illumcorr', action='store_true',
    help='correct images for illumination artifacts before stitching')
init_stitch_group.add_argument(
    '-t', '--thresh', action='store_true',
    help='rescale pixel values between min value and a threshold level')
init_stitch_group.add_argument(
    '--thresh_value', type=int, default=None,
    help='fixed pixel value for threshold')
init_stitch_group.add_argument(
    '--thresh_percent', type=float, default=99.9,
    help='percentage of pixel values below threshold (default: 99.9)')

for name in subparsers.choices:
    subparsers.choices[name].set_defaults(handler=Illuminati.call)
