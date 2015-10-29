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
    '-a', '--align', action='store_true',
    help='align images between cycles')
init_stitch_group.add_argument(
    '-i', '--illumcorr', action='store_true',
    help='correct images for illumination artifacts')
init_stitch_group.add_argument(
    '-c', '--clip', action='store_true',
    help='clip pixel values above a certain level to level value, '
         'i.e. rescale images between min value and a clip level')
init_stitch_group.add_argument(
    '--clip_value', type=int, default=None,
    help='define a fixed pixel value for clip level')
init_stitch_group.add_argument(
    '--clip_percent', type=float, default=99.9,
    help='define percentage of pixel values below clip level (default: 99.9)')

for name in subparsers.choices:
    subparsers.choices[name].set_defaults(handler=Illuminati.call)
